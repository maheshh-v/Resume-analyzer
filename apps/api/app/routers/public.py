"""White-label public API surface: POST /verify and GET /reports/{id}.

Key-authenticated (not Supabase), rate-limited and quota-limited per key. /verify accepts a resume
(base64 PDF or plain text) + JD, kicks off an async verification, consumes one unit of quota, emits
one Stripe meter event (scaffold), and returns a report_id to poll.
"""

import base64
import binascii
import io

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.meter import record_verification_usage
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.public_report import PublicReport
from app.pipeline.text_extraction import extract_text_from_pdf
from app.public_api.auth import require_api_key
from app.public_api.rate_limit import rate_limited_api_key
from app.public_api.verify_job import run_public_verification
from app.schemas.public import PublicReportOut, VerifyAccepted, VerifyRequest
from app.storage.report_storage import signed_report_url

router = APIRouter(prefix="/api/v1/public", tags=["public-api"])


def _decode_resume(resume: str) -> str:
    """Accept either a base64-encoded PDF or plain resume text. Only text that base64-decodes to a
    real PDF is treated as a PDF; everything else is used verbatim as resume text."""
    raw = (resume or "").strip()
    if not raw:
        return ""
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        decoded = None
    if decoded and decoded[:5] == b"%PDF-":
        try:
            return extract_text_from_pdf(io.BytesIO(decoded)).full_text
        except Exception as exc:  # a corrupt PDF is a client error, not a 500
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not read the PDF: {exc}") from exc
    return resume


@router.post("/verify", response_model=VerifyAccepted, status_code=status.HTTP_202_ACCEPTED)
async def public_verify(
    payload: VerifyRequest,
    background_tasks: BackgroundTasks,
    key: ApiKey = Depends(rate_limited_api_key),
    db: AsyncSession = Depends(get_db),
) -> VerifyAccepted:
    if key.quota_exhausted:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Monthly quota exhausted for this API key")

    resume_text = _decode_resume(payload.resume)
    if not resume_text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty resume")
    if not payload.jd.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty job description")

    report = PublicReport(api_key_id=key.id, status="pending", webhook_url=payload.webhook_url)
    db.add(report)
    key.usage_count += 1
    await db.flush()
    report_id = report.id
    await db.commit()

    # One metered usage event per accepted verification (scaffold: no-op unless the key is onboarded).
    await record_verification_usage(key)

    background_tasks.add_task(
        run_public_verification,
        report_id=report_id,
        resume_text=resume_text,
        jd_text=payload.jd,
        org_name=key.org_name,
        logo_url=key.logo_url,
        webhook_url=payload.webhook_url,
    )
    return VerifyAccepted(
        report_id=report_id, status="pending", status_url=f"/api/v1/public/reports/{report_id}"
    )


@router.get("/reports/{report_id}", response_model=PublicReportOut)
async def get_public_report(
    report_id: str,
    key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> PublicReportOut:
    report = await db.get(PublicReport, report_id)
    # Scoped to the creating key — a different key gets a 404, never another org's report.
    if report is None or report.api_key_id != key.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")

    return PublicReportOut(
        report_id=report.id,
        status=report.status,
        report=report.report_json,
        pdf_storage_path=report.pdf_storage_path,
        pdf_url=await signed_report_url(report.pdf_storage_path),
        error=report.error,
        created_at=report.created_at.isoformat() if report.created_at else None,
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
    )
