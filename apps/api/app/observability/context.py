"""Ambient LLM-call context, propagated via contextvars.

The pipeline stages (extract_claims, interview generation, ...) take a resume string and an LLM
client — not a candidate id. Rather than thread candidate/job ids through every stage signature
just for tracing, the entry points (orchestrate, interview + job routers) set an ambient context
and the LLM client reads it. contextvars copy into any asyncio task spawned within the block, so
this works across the awaits inside a single request/background task.
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMCallContext:
    candidate_id: str | None = None
    job_id: str | None = None


_current: contextvars.ContextVar[LLMCallContext | None] = contextvars.ContextVar(
    "llm_call_context", default=None
)


def current_context() -> LLMCallContext | None:
    return _current.get()


@contextlib.contextmanager
def llm_call_context(*, candidate_id: str | None = None, job_id: str | None = None) -> Iterator[None]:
    token = _current.set(LLMCallContext(candidate_id=candidate_id, job_id=job_id))
    try:
        yield
    finally:
        _current.reset(token)
