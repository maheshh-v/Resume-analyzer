"""The single entrypoint pipeline code uses to talk to an LLM.

Wraps provider selection (Gemini default, OpenAI fallback, Fake for tests), retries on
transient failures, best-effort cost accounting, and Langfuse tracing (no-op if Langfuse
keys aren't configured — this must work with zero external credentials for tests/local dev).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel

from app.config import Settings, get_settings
from app.llm.errors import LLMTransientError, LLMUnavailableError
from app.llm.provider import FakeProvider, GeminiProvider, LLMProvider, OpenAIProvider

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

# Retry budget: 3 tries on the primary model (waits 1s, 2s between), then 2 tries on the
# fallback model if one is configured. Worst case adds ~5s of waiting before a clean 503.
_PRIMARY_ATTEMPTS = 3
_FALLBACK_ATTEMPTS = 2
_BACKOFF_BASE_SECONDS = 1.0
_BACKOFF_MAX_SECONDS = 8.0

# Rough per-1M-token USD pricing for the cost line in the README. Best-effort estimate,
# not billing-accurate — update as providers change pricing.
_PRICING_PER_1M_TOKENS = {
    "gemini-3.5-flash": {"input": 0.30, "output": 2.50},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


@dataclass
class LLMCallResult:
    data: BaseModel
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


def _estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = _PRICING_PER_1M_TOKENS.get(model)
    if not prices:
        return 0.0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


def _build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    if settings.llm_provider == "fake":
        return FakeProvider()
    return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)


def _build_fallback_provider(settings: Settings) -> LLMProvider | None:
    """A second model to try when the primary is overloaded. Gemini-only for now: the
    fallback shares the primary's API key, so it costs nothing to configure."""
    if settings.llm_provider != "gemini":
        return None
    fallback = settings.gemini_fallback_model.strip()
    if not fallback or fallback == settings.gemini_model:
        return None
    return GeminiProvider(api_key=settings.gemini_api_key, model=fallback)


class LangfuseTracer:
    """Thin wrapper so the rest of the app never branches on 'is Langfuse configured'."""

    def __init__(self, settings: Settings):
        self._enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)
        self._client = None
        if self._enabled:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )

    @contextlib.contextmanager
    def span(self, name: str, **metadata):
        if not self._enabled:
            yield None
            return
        generation = self._client.start_generation(name=name, metadata=metadata)
        try:
            yield generation
        finally:
            generation.end()


class LLMClient:
    def __init__(self, provider: LLMProvider | None = None, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._provider = provider or _build_provider(self._settings)
        # Only wire a fallback when we built the provider ourselves — an injected provider
        # (tests, evals) must be the only thing that ever gets called.
        self._fallback = None if provider is not None else _build_fallback_provider(self._settings)
        self._tracer = LangfuseTracer(self._settings)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def generate_structured(
        self, *, system: str, user: str, schema: type[T], prompt_version: str, trace_name: str
    ) -> LLMCallResult:
        """Call the primary model with exponential-backoff retries on transient failures
        (429/5xx/network), then the fallback model if configured. Non-transient errors
        propagate immediately; exhausting every attempt raises LLMUnavailableError, which
        the API layer turns into a clean 503."""
        plan: list[tuple[LLMProvider, int]] = [(self._provider, _PRIMARY_ATTEMPTS)]
        if self._fallback is not None:
            plan.append((self._fallback, _FALLBACK_ATTEMPTS))

        last_transient: LLMTransientError | None = None
        for stage, (provider, max_attempts) in enumerate(plan):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await self._call_once(
                        provider, system=system, user=user, schema=schema,
                        prompt_version=prompt_version, trace_name=trace_name,
                    )
                except LLMTransientError as exc:
                    last_transient = exc
                    logger.warning("LLM transient failure (attempt %d/%d): %s", attempt, max_attempts, exc)
                    if attempt < max_attempts:
                        delay = min(_BACKOFF_BASE_SECONDS * 2 ** (attempt - 1), _BACKOFF_MAX_SECONDS)
                        await asyncio.sleep(delay)
                except Exception:
                    if stage == 0:
                        raise
                    # The fallback model failing for a non-transient reason (e.g. this API key
                    # can't access it) shouldn't mask the real story: the primary is overloaded.
                    logger.exception("Fallback model failed non-transiently; reporting primary overload")
                    break

        raise LLMUnavailableError() from last_transient

    async def _call_once(
        self, provider: LLMProvider, *, system: str, user: str, schema: type[T], prompt_version: str, trace_name: str
    ) -> LLMCallResult:
        start = time.perf_counter()
        with self._tracer.span(trace_name, prompt_version=prompt_version, provider=provider.name):
            result = await provider.generate_structured(system=system, user=user, schema=schema)
        latency_ms = int((time.perf_counter() - start) * 1000)
        cost = _estimate_cost_usd(result.model, result.input_tokens, result.output_tokens)
        return LLMCallResult(
            data=result.data,
            model=result.model,
            prompt_version=prompt_version,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def set_default_client(client: LLMClient | None) -> None:
    """Test seam: install a client (typically wrapping FakeProvider) as the process-wide
    singleton, or pass None to force get_llm_client() to rebuild from current settings."""
    global _default_client
    _default_client = client
