from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.candidate import Candidate
from app.models.evidence import Evidence
from app.models.job import Job
from app.models.user import User
from app.pipeline.match import ClaimLike, RequirementLike, match_claims_to_requirements
from app.pipeline.orchestrate import process_candidate_resume
from app.routers.jobs import get_owned_job
from app.schemas.candidate import CandidateCreate, CandidateDetailOut, CandidateOut

router = APIRouter(tags=["candidates"])

_MAX_RESUME_BYTES = 10 * 1024 * 1024


async def get_owned_candidate(candidate_id: str, user: User, db: AsyncSession) -> Candidate:
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.claims))
        .where(Candidate.id == candidate_id, Candidate.owner_user_id == user.id)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return candidate


@router.post("/jobs/{job_id}/candidates", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    job_id: str,
    payload: CandidateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    await get_owned_job(job_id, user, db)  # ownership check
    candidate = Candidate(
        owner_user_id=user.id,
        job_id=job_id,
        name=payload.name,
        email=payload.email,
        github_login=payload.github_login,
        linkedin_url=payload.linkedin_url,
        status="pending",
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateOut])
async def list_candidates(
    job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Candidate]:
    await get_owned_job(job_id, user, db)
    result = await db.execute(
        select(Candidate).where(Candidate.job_id == job_id, Candidate.owner_user_id == user.id)
        .order_by(Candidate.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/candidates/{candidate_id}/resume", response_model=CandidateOut)
async def upload_resume(
    candidate_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    candidate = await get_owned_candidate(candidate_id, user, db)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF resumes are supported")

    content = await file.read()
    if len(content) > _MAX_RESUME_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File too large (max 10MB)")

    candidate.status = "processing"
    candidate.status_detail = None
    await db.commit()

    background_tasks.add_task(
        process_candidate_resume,
        candidate_id=candidate.id,
        filename=file.filename,
        file_bytes=content,
        session_factory=SessionLocal,
    )
    await db.refresh(candidate)
    return candidate


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailOut)
async def get_candidate_detail(
    candidate_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CandidateDetailOut:
    candidate = await get_owned_candidate(candidate_id, user, db)

    job_result = await db.execute(select(Job).options(selectinload(Job.requirements)).where(Job.id == candidate.job_id))
    job = job_result.scalar_one()

    claim_ids = [c.id for c in candidate.claims]
    evidence_rows: list[Evidence] = []
    if claim_ids:
        evidence_result = await db.execute(select(Evidence).where(Evidence.claim_id.in_(claim_ids)))
        evidence_rows = list(evidence_result.scalars().all())

    requirements = [
        RequirementLike(
            id=r.id, skill=r.skill, normalized_skill=r.normalized_skill, importance=r.importance, min_years=r.min_years
        )
        for r in job.requirements
    ]
    claims = [
        ClaimLike(id=c.id, claim_text=c.claim_text, normalized_skill=c.normalized_skill, asserted_years=c.asserted_years)
        for c in candidate.claims
    ]
    matches = match_claims_to_requirements(requirements, claims)

    return CandidateDetailOut(
        candidate=CandidateOut.model_validate(candidate),
        claims=[c for c in candidate.claims],
        evidence=evidence_rows,
        matches=[
            {
                "requirement_id": m.requirement_id,
                "skill": m.skill,
                "importance": m.importance,
                "status": m.status,
                "matching_claim_ids": m.matching_claim_ids,
                "note": m.note,
            }
            for m in matches
        ],
        extraction_stats={"claim_count": len(candidate.claims), "evidence_count": len(evidence_rows)},
    )
