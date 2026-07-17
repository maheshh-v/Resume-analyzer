from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.llm.client import LLMClient, get_llm_client
from app.models.candidate import Candidate
from app.models.job import Job, JobRequirement
from app.models.user import User
from app.observability.context import llm_call_context
from app.pipeline.extract_jd import extract_job_requirements
from app.schemas.job import JobCreate, JobOut, JobRequirementsReplace, JobSummaryOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def get_owned_job(job_id: str, user: User, db: AsyncSession) -> Job:
    # populate_existing: without it, a Job already in this session's identity map (e.g.
    # re-fetched after mutating its requirements in the same request) keeps its stale,
    # already-loaded `requirements` collection — selectinload only fires for a relationship
    # that isn't loaded yet, so a caller re-querying after a delete+insert would silently see
    # the pre-mutation rows despite the DB itself being correct.
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.requirements))
        .where(Job.id == job_id, Job.owner_user_id == user.id)
        .execution_options(populate_existing=True)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> Job:
    job = Job(owner_user_id=user.id, title=payload.title, jd_raw=payload.jd_raw, requirements_status="draft")
    db.add(job)
    await db.flush()

    # No candidate yet at JD time; job_id tags the trace, and cost logging (candidate-scoped)
    # correctly skips this call.
    with llm_call_context(job_id=job.id):
        drafts = await extract_job_requirements(payload.jd_raw, llm)
    for ordinal, draft in enumerate(drafts):
        db.add(
            JobRequirement(
                job_id=job.id,
                ordinal=ordinal,
                skill=draft.skill,
                normalized_skill=draft.normalized_skill,
                category=draft.category,
                importance=draft.importance,
                min_years=draft.min_years,
                evidence_criteria=draft.evidence_criteria,
                source_span_start=draft.source_span_start,
                source_span_end=draft.source_span_end,
            )
        )
    await db.commit()
    return await get_owned_job(job.id, user, db)


@router.get("", response_model=list[JobSummaryOut])
async def list_jobs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        select(Job, func.count(Candidate.id))
        .outerjoin(Candidate, Candidate.job_id == Job.id)
        .where(Job.owner_user_id == user.id)
        .group_by(Job.id)
        .order_by(Job.created_at.desc())
    )
    rows = result.all()
    return [
        JobSummaryOut(
            id=job.id,
            title=job.title,
            requirements_status=job.requirements_status,
            created_at=job.created_at,
            candidate_count=count,
        )
        for job, count in rows
    ]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Job:
    return await get_owned_job(job_id, user, db)


@router.put("/{job_id}/requirements", response_model=JobOut)
async def replace_requirements(
    job_id: str,
    payload: JobRequirementsReplace,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    """The recruiter's 30-second review/edit pass before anything downstream runs."""
    job = await get_owned_job(job_id, user, db)
    for existing in list(job.requirements):
        await db.delete(existing)
    await db.flush()

    for ordinal, req in enumerate(payload.requirements):
        db.add(
            JobRequirement(
                job_id=job.id,
                ordinal=ordinal,
                skill=req.skill,
                normalized_skill=req.normalized_skill.lower().strip(),
                category=req.category,
                importance=req.importance,
                min_years=req.min_years,
                evidence_criteria=req.evidence_criteria,
            )
        )
    job.requirements_status = "reviewed"
    await db.commit()
    return await get_owned_job(job_id, user, db)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    job = await get_owned_job(job_id, user, db)
    await db.delete(job)
    await db.commit()
