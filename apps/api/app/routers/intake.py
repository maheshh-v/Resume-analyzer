"""Bulk candidate intake: multi-PDF upload, CSV/XLSX sheet import, and the public apply link.

The one-dialog-per-candidate flow doesn't survive contact with a real hiring funnel; these are
the three ways candidates actually arrive in volume. All three funnel into the exact same
process_candidate_resume pipeline as the single-upload path — same citation guardrail, same
Evidence Ledger — so bulk intake never becomes a side door around verification.

The apply-link routes (`/apply/{token}/*`) are PUBLIC by design, mirroring the interview
portal: an unguessable token scopes every lookup, rotating it invalidates shared links, and a
per-token rate limit keeps drive-by uploads in check.
"""

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.session import SessionLocal, get_db
from app.intake.ingest import ResumeFetchItem, ingest_sheet_resumes
from app.intake.naming import candidate_name_from_filename
from app.intake.sheet import parse_candidate_sheet
from app.ledger import append_event
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User
from app.pipeline.orchestrate import process_candidate_resume
from app.public_api.rate_limit import allow_hit
from app.routers.jobs import get_owned_job
from app.schemas.candidate import CandidateOut
from app.schemas.intake import (
    ApplicationReceivedOut,
    ApplyLinkOut,
    BulkUploadOut,
    PublicJobOut,
    SheetImportOut,
)

router = APIRouter(tags=["intake"])

MAX_BULK_FILES = 20
_MAX_RESUME_BYTES = 10 * 1024 * 1024
_MAX_SHEET_BYTES = 5 * 1024 * 1024
_JD_PREVIEW_CHARS = 2000


# --- Bulk PDF upload -------------------------------------------------------------------


@router.post(
    "/jobs/{job_id}/candidates/bulk-upload",
    response_model=BulkUploadOut,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_upload_resumes(
    job_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkUploadOut:
    await get_owned_job(job_id, user, db)  # ownership check
    if len(files) > MAX_BULK_FILES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Too many files — upload at most {MAX_BULK_FILES} at a time"
        )

    created: list[Candidate] = []
    errors: list[str] = []
    pipeline_jobs: list[tuple[str, str, bytes]] = []
    for file in files:
        label = file.filename or "unnamed file"
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            errors.append(f"{label}: only PDF resumes are supported")
            continue
        content = await file.read()
        if len(content) > _MAX_RESUME_BYTES:
            errors.append(f"{label}: file too large (max 10MB)")
            continue

        # status starts at "processing" (not "pending"): background tasks run sequentially after
        # the response, and a late-queue candidate must show a spinner, not an upload prompt.
        candidate = Candidate(
            owner_user_id=user.id,
            job_id=job_id,
            name=candidate_name_from_filename(file.filename),
            status="processing",
        )
        db.add(candidate)
        await db.flush()
        await append_event(
            db,
            candidate_id=candidate.id,
            event_type="candidate_created",
            actor_type="human",
            actor_id=user.email,
            payload={"name": candidate.name, "job_id": job_id, "intake": "bulk_upload", "filename": file.filename},
        )
        created.append(candidate)
        pipeline_jobs.append((candidate.id, file.filename, content))

    await db.commit()
    for candidate in created:
        await db.refresh(candidate)
    for candidate_id, filename, content in pipeline_jobs:
        background_tasks.add_task(
            process_candidate_resume,
            candidate_id=candidate_id,
            filename=filename,
            file_bytes=content,
            session_factory=SessionLocal,
        )
    return BulkUploadOut(created=[CandidateOut.model_validate(c) for c in created], errors=errors)


# --- CSV / XLSX sheet import -----------------------------------------------------------


@router.post(
    "/jobs/{job_id}/candidates/import",
    response_model=SheetImportOut,
    status_code=status.HTTP_201_CREATED,
)
async def import_candidate_sheet(
    job_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SheetImportOut:
    await get_owned_job(job_id, user, db)  # ownership check
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a .csv or .xlsx file")
    content = await file.read()
    if len(content) > _MAX_SHEET_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sheet too large (max 5MB)")

    parsed = parse_candidate_sheet(content, filename)
    if not parsed.rows:
        # Nothing importable at all — surface why as a request error the dialog can show.
        detail = "; ".join(parsed.errors) if parsed.errors else "No importable rows found"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail)

    created: list[Candidate] = []
    fetch_items: list[ResumeFetchItem] = []
    for row in parsed.rows:
        candidate = Candidate(
            owner_user_id=user.id,
            job_id=job_id,
            name=row.name,
            email=row.email,
            github_login=row.github_login,
            linkedin_url=row.linkedin_url,
            # With a resume URL the pipeline starts immediately (spinner); without one the
            # recruiter still has the per-row manual upload prompt.
            status="processing" if row.resume_url else "pending",
        )
        db.add(candidate)
        await db.flush()
        await append_event(
            db,
            candidate_id=candidate.id,
            event_type="candidate_created",
            actor_type="human",
            actor_id=user.email,
            payload={"name": row.name, "job_id": job_id, "intake": "sheet_import", "row": row.row_number},
        )
        created.append(candidate)
        if row.resume_url:
            fetch_items.append(
                ResumeFetchItem(candidate_id=candidate.id, candidate_name=row.name, resume_url=row.resume_url)
            )

    await db.commit()
    for candidate in created:
        await db.refresh(candidate)
    if fetch_items:
        background_tasks.add_task(ingest_sheet_resumes, items=fetch_items, session_factory=SessionLocal)
    return SheetImportOut(
        created=[CandidateOut.model_validate(c) for c in created],
        errors=parsed.errors,
        fetching_count=len(fetch_items),
    )


# --- Public apply link -----------------------------------------------------------------


@router.post("/jobs/{job_id}/apply-link", response_model=ApplyLinkOut)
async def create_or_rotate_apply_link(
    job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ApplyLinkOut:
    """Creates the job's public apply link, or rotates it (invalidating the old URL) if one exists."""
    job = await get_owned_job(job_id, user, db)
    job.apply_token = secrets.token_urlsafe(24)
    await db.commit()
    return ApplyLinkOut(apply_token=job.apply_token, apply_url_path=f"/apply/{job.apply_token}")


@router.delete("/jobs/{job_id}/apply-link", status_code=status.HTTP_204_NO_CONTENT)
async def disable_apply_link(
    job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    job = await get_owned_job(job_id, user, db)
    job.apply_token = None
    await db.commit()


async def _job_by_apply_token(token: str, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.apply_token == token))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This application link is no longer active")
    return job


@router.get("/apply/{token}", response_model=PublicJobOut)
async def get_public_job(token: str, db: AsyncSession = Depends(get_db)) -> PublicJobOut:
    job = await _job_by_apply_token(token, db)
    return PublicJobOut(job_title=job.title, jd_preview=job.jd_raw[:_JD_PREVIEW_CHARS])


@router.post("/apply/{token}", response_model=ApplicationReceivedOut, status_code=status.HTTP_201_CREATED)
async def submit_application(
    token: str,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    name: str = Form(...),
    email: str = Form(...),
    github_login: str = Form(""),
    linkedin_url: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> ApplicationReceivedOut:
    job = await _job_by_apply_token(token, db)

    limit = get_settings().apply_rate_limit_per_min
    if limit > 0 and not allow_hit(f"apply:{token}", limit):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many applications right now — try again in a minute"
        )

    name = name.strip()
    email = email.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name is required")
    if "@" not in email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A valid email is required")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF resumes are supported")
    content = await file.read()
    if len(content) > _MAX_RESUME_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File too large (max 10MB)")

    candidate = Candidate(
        owner_user_id=job.owner_user_id,  # the recruiter owns applicants, same as manual entry
        job_id=job.id,
        name=name,
        email=email,
        github_login=github_login.strip() or None,
        linkedin_url=linkedin_url.strip() or None,
        status="processing",
    )
    db.add(candidate)
    await db.flush()
    await append_event(
        db,
        candidate_id=candidate.id,
        event_type="candidate_applied",
        actor_type="candidate",
        payload={"name": name, "job_id": job.id, "intake": "apply_link"},
    )
    await db.commit()

    background_tasks.add_task(
        process_candidate_resume,
        candidate_id=candidate.id,
        filename=file.filename,
        file_bytes=content,
        session_factory=SessionLocal,
    )
    # Deliberately no candidate id in the response — the applicant gets an acknowledgement,
    # not a handle into the recruiter's workspace.
    return ApplicationReceivedOut()
