"""Recruiter-facing observability: per-candidate LLM cost + latency breakdown.

Reads the append-only llm_call_log telemetry (metadata only) and rolls it up per pipeline stage.
Ownership-gated exactly like the rest of the recruiter surface — a recruiter can only see costs
for their own candidates.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.llm_call_log import LLMCallLog
from app.models.user import User
from app.routers.candidates import get_owned_candidate
from app.schemas.observability import LLMCostSummary, LLMStageCost

# Explicit /api/v1 prefix per spec. The rest of the app is unversioned; the new observability
# and public surfaces adopt versioning going forward (see HANDOFF.md).
router = APIRouter(prefix="/api/v1/candidates", tags=["observability"])


@router.get("/{candidate_id}/llm-costs", response_model=LLMCostSummary)
async def candidate_llm_costs(
    candidate_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LLMCostSummary:
    await get_owned_candidate(candidate_id, user, db)  # ownership check (404s if not theirs)

    result = await db.execute(
        select(LLMCallLog)
        .where(LLMCallLog.candidate_id == candidate_id)
        .order_by(LLMCallLog.created_at)
    )
    rows = list(result.scalars().all())

    stages: dict[str, dict] = {}
    for row in rows:
        stage = stages.setdefault(
            row.pipeline_stage,
            {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "latency_ms_total": 0,
                "max_retry_count": 0,
                "models": set(),
            },
        )
        stage["calls"] += 1
        stage["input_tokens"] += row.input_tokens
        stage["output_tokens"] += row.output_tokens
        stage["cost_usd"] += row.cost_usd
        stage["latency_ms_total"] += row.latency_ms
        stage["max_retry_count"] = max(stage["max_retry_count"], row.retry_count)
        stage["models"].add(row.model)

    per_stage = [
        LLMStageCost(
            pipeline_stage=name,
            calls=s["calls"],
            input_tokens=s["input_tokens"],
            output_tokens=s["output_tokens"],
            cost_usd=round(s["cost_usd"], 6),
            latency_ms_total=s["latency_ms_total"],
            max_retry_count=s["max_retry_count"],
            models=sorted(s["models"]),
        )
        for name, s in stages.items()
    ]
    per_stage.sort(key=lambda s: s.pipeline_stage)

    return LLMCostSummary(
        candidate_id=candidate_id,
        total_cost_usd=round(sum(s.cost_usd for s in per_stage), 6),
        total_calls=sum(s.calls for s in per_stage),
        total_input_tokens=sum(s.input_tokens for s in per_stage),
        total_output_tokens=sum(s.output_tokens for s in per_stage),
        total_latency_ms=sum(s.latency_ms_total for s in per_stage),
        per_stage=per_stage,
    )
