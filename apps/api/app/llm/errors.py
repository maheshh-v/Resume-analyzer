"""Typed LLM failure taxonomy.

Providers translate SDK-specific exceptions into these so the client's retry logic and the
API's error responses never depend on which vendor SDK raised what.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all LLM-layer failures."""


class LLMTransientError(LLMError):
    """Retryable failure: model overloaded (503), rate-limited (429), transient 5xx, or a
    network/timeout blip. The client retries these with exponential backoff."""


class LLMUnavailableError(LLMError):
    """All retries (and the fallback model, if configured) are exhausted. The message is
    user-facing — the API surfaces it verbatim as a 503 detail."""

    def __init__(self, message: str | None = None):
        super().__init__(
            message
            or "The AI model is temporarily overloaded. Nothing was lost — please try again in a minute."
        )
