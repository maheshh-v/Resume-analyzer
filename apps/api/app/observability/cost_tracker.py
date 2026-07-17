"""Best-effort per-call cost/latency sink -> llm_call_log.

Writes on its OWN short-lived session, decoupled from the pipeline transaction, so:
  - a logging failure can never roll back or fail the actual verification work, and
  - the record persists even if the pipeline later errors out.

Metadata only — no prompt/response bodies (see the model docstring). Every failure is swallowed
with a warning; observability must never be load-bearing.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.session import SessionLocal
from app.models.llm_call_log import LLMCallLog

logger = logging.getLogger(__name__)


async def record_llm_call(
    *,
    candidate_id: str | None,
    job_id: str | None,
    pipeline_stage: str,
    model: str,
    provider: str | None,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    retry_count: int,
    session_factory: async_sessionmaker | None = None,
) -> None:
    factory = session_factory or SessionLocal
    try:
        async with factory() as db:
            db.add(
                LLMCallLog(
                    candidate_id=candidate_id,
                    job_id=job_id,
                    pipeline_stage=pipeline_stage,
                    model=model,
                    provider=provider,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                )
            )
            await db.commit()
    except Exception:  # telemetry must never break the pipeline
        logger.warning(
            "cost_tracker: failed to record llm call (candidate=%s stage=%s)",
            candidate_id,
            pipeline_stage,
            exc_info=True,
        )
