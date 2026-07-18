"""Retry/backoff/fallback behavior of LLMClient, and the API-level 503 it produces.

A Gemini 503 ("model overloaded") must never surface as a raw stack trace: the client
retries with backoff, then tries the fallback model, then raises LLMUnavailableError,
which the API middleware turns into a clean 503 with a user-facing detail message.
"""

import pytest
from pydantic import BaseModel

import app.llm.client as client_module
from app.llm.client import LLMClient, set_default_client
from app.llm.errors import LLMTransientError, LLMUnavailableError
from app.llm.provider import LLMProvider, StructuredResult


class EchoSchema(BaseModel):
    value: str


class FlakyProvider(LLMProvider):
    """Raises a transient error for the first `failures` calls, then succeeds."""

    name = "flaky"

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    async def generate_structured(self, *, system, user, schema):
        self.calls += 1
        if self.calls <= self.failures:
            raise LLMTransientError("503 UNAVAILABLE: model overloaded")
        return StructuredResult(data=schema.model_validate({"value": "ok"}), model="flaky-model")


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch):
    monkeypatch.setattr(client_module, "_BACKOFF_BASE_SECONDS", 0.0)
    monkeypatch.setattr(client_module, "_BACKOFF_MAX_SECONDS", 0.0)


async def _generate(client: LLMClient):
    return await client.generate_structured(
        system="s", user="u", schema=EchoSchema, prompt_version="test.v1", trace_name="test"
    )


async def test_transient_errors_are_retried_until_success():
    provider = FlakyProvider(failures=2)
    result = await _generate(LLMClient(provider=provider))
    assert provider.calls == 3
    assert result.data.value == "ok"


async def test_exhausted_retries_raise_clean_typed_error():
    provider = FlakyProvider(failures=99)
    with pytest.raises(LLMUnavailableError) as excinfo:
        await _generate(LLMClient(provider=provider))
    assert provider.calls == client_module._PRIMARY_ATTEMPTS
    assert "overloaded" in str(excinfo.value)


async def test_fallback_model_is_tried_after_primary_exhausted():
    primary = FlakyProvider(failures=99)
    fallback = FlakyProvider(failures=0)
    client = LLMClient(provider=primary)
    client._fallback = fallback
    result = await _generate(client)
    assert primary.calls == client_module._PRIMARY_ATTEMPTS
    assert fallback.calls == 1
    assert result.data.value == "ok"


async def test_non_transient_errors_propagate_immediately():
    class BoomProvider(LLMProvider):
        name = "boom"
        calls = 0

        async def generate_structured(self, *, system, user, schema):
            self.calls += 1
            raise ValueError("bad schema")

    provider = BoomProvider()
    with pytest.raises(ValueError):
        await _generate(LLMClient(provider=provider))
    assert provider.calls == 1


async def test_api_returns_503_with_friendly_detail_when_llm_unavailable(client):
    set_default_client(LLMClient(provider=FlakyProvider(failures=99)))
    response = await client.post("/api/v1/jobs", json={"title": "Backend Engineer", "jd_raw": "Python. FastAPI."})
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "overloaded" in detail.lower()
    assert "try again" in detail.lower()
