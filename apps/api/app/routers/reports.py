from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.interview import Interview, InterviewQuestion
from app.models.job import Job
from app.models.user import User
from app.pipeline.evidence.consistency import ConsistencyFinding
from app.pipeline.match import ClaimLike, RequirementLike, match_claims_to_requirements
from app.pipeline.report import EvidenceRow, QAExchange, build_hiring_summary
from app.routers.candidates import get_owned_candidate
from app.schemas.report import DecisionCreate, DecisionOut, HiringSummaryOut

router = APIRouter(tags=["reports"])


@router.get("/candidates/{candidate_id}/report", response_model=HiringSummaryOut)
async def get_hiring_summary(
    candidate_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> HiringSummaryOut:
    candidate = await get_owned_candidate(candidate_id, user, db)

    job_result = await db.execute(select(Job).options(selectinload(Job.requirements)).where(Job.id == candidate.job_id))
    job = job_result.scalar_one()

    claim_ids = [c.id for c in candidate.claims]
    evidence_rows: list[Evidence] = []
    if claim_ids:
        evidence_result = await db.execute(select(Evidence).where(Evidence.claim_id.in_(claim_ids)))
        evidence_rows = list(evidence_result.scalars().all())

    requirements = [
        RequirementLike(id=r.id, skill=r.skill, normalized_skill=r.normalized_skill, importance=r.importance, min_years=r.min_years)
        for r in job.requirements
    ]
    claims = [
        ClaimLike(id=c.id, claim_text=c.claim_text, normalized_skill=c.normalized_skill, asserted_years=c.asserted_years)
        for c in candidate.claims
    ]
    matches = match_claims_to_requirements(requirements, claims)

    consistency_summaries = {e.summary for e in evidence_rows if e.source_type == "consistency"}
    consistency_findings = [ConsistencyFinding(finding_type="consistency", claim_ids=[], summary=s) for s in consistency_summaries]

    interview_result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.questions).selectinload(InterviewQuestion.answer))
        .where(Interview.candidate_id == candidate_id)
        .order_by(Interview.created_at.desc())
    )
    latest_interview = interview_result.scalars().first()
    transcript: list[QAExchange] = []
    if latest_interview:
        for q in latest_interview.questions:
            transcript.append(
                QAExchange(
                    depth=q.depth,
                    question_text=q.question_text,
                    rationale=q.rationale,
                    answer_text=q.answer.answer_text if q.answer else None,
                    specificity_verdict=q.answer.specificity_verdict if q.answer else None,
                    specificity_notes=q.answer.specificity_notes if q.answer else None,
                    review_flags=q.answer.review_flags if q.answer else [],
                )
            )

    summary = build_hiring_summary(
        matches=matches,
        evidence=[EvidenceRow(claim_id=e.claim_id, source_type=e.source_type, verdict=e.verdict, summary=e.summary, artifact_url=e.artifact_url) for e in evidence_rows],
        consistency_findings=consistency_findings,
        transcript=transcript,
        claim_text_by_id={c.id: c.claim_text for c in candidate.claims},
    )

    return HiringSummaryOut(
        evidence_coverage_count=summary.evidence_coverage_count,
        evidence_coverage_total=summary.evidence_coverage_total,
        conflicts=summary.conflicts,
        matrix=[m.__dict__ for m in summary.matrix],
        verified_skills=[m.__dict__ for m in summary.verified_skills],
        needs_manual_verification=[m.__dict__ for m in summary.needs_manual_verification],
        technical_strengths=summary.technical_strengths,
        weak_areas=summary.weak_areas,
        suggested_followups=summary.suggested_followups,
        transcript=[t.__dict__ for t in summary.transcript],
    )


@router.post("/candidates/{candidate_id}/decision", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
async def record_decision(
    candidate_id: str,
    payload: DecisionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Decision:
    candidate = await get_owned_candidate(candidate_id, user, db)
    if payload.verdict not in ("advance", "hold", "decline"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "verdict must be one of: advance, hold, decline")

    decision = Decision(
        candidate_id=candidate.id,
        job_id=candidate.job_id,
        decided_by_user_id=user.id,
        verdict=payload.verdict,
        rationale=payload.rationale,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return decision
