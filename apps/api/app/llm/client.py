"""The single entrypoint pipeline code uses to talk to an LLM.

Wraps provider selection (Gemini default, OpenAI fallback, Fake for tests), retries on
transient failures, best-effort cost accounting, and Langfuse tracing (no-op if Langfuse
keys aren't configured — this must work with zero external credentials for tests/local dev).
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from app.llm.provider import FakeProvider, GeminiProvider, LLMProvider, OpenAIProvider

T = TypeVar("T", bound=BaseModel)

# Rough per-1M-token USD pricing for the cost line in the README. Best-effort estimate,
# not billing-accurate — update as providers change pricing.
_PRICING_PER_1M_TOKENS = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
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
        self._tracer = LangfuseTracer(self._settings)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def generate_structured(
        self, *, system: str, user: str, schema: type[T], prompt_version: str, trace_name: str
    ) -> LLMCallResult:
        start = time.perf_counter()
        with self._tracer.span(trace_name, prompt_version=prompt_version, provider=self._provider.name):
            result = await self._provider.generate_structured(system=system, user=user, schema=schema)
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
