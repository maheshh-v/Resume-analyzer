"""Storage routing for white-label branded report PDFs.

Uploads to the private Supabase Storage *reports* bucket when Storage is configured and
`USE_LOCAL_STORAGE` is off; otherwise falls back to local disk (dev/testing without creds). The
service role key lives only in settings — it is never logged, returned, or committed.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60


def _use_supabase() -> bool:
    settings = get_settings()
    return bool(
        not settings.use_local_storage and settings.supabase_url and settings.supabase_service_role_key
    )


async def store_report_pdf(*, report_id: str, content: bytes) -> str:
    """Persist a branded report PDF and return its storage path."""
    settings = get_settings()
    if not _use_supabase():
        from app.storage.local_storage import upload_resume  # local fallback, same interface

        return await upload_resume(candidate_id=report_id, filename="report.pdf", content=content)

    from app.storage.supabase_storage import upload_object

    return await upload_object(
        bucket=settings.supabase_reports_bucket,
        path=f"{report_id}/report.pdf",
        content=content,
        content_type="application/pdf",
    )


async def signed_report_url(storage_path: str | None, *, expires_in: int = SEVEN_DAYS_SECONDS) -> str | None:
    """A signed URL (default 7 days) for a report PDF in Supabase Storage, or None when on local
    disk / unconfigured. Best-effort — a signing failure returns None rather than raising."""
    if not storage_path or not _use_supabase():
        return None
    settings = get_settings()
    try:
        from app.storage.supabase_storage import create_signed_url

        return await create_signed_url(
            storage_path, bucket=settings.supabase_reports_bucket, expires_in=expires_in
        )
    except Exception:
        logger.info("report_storage: could not sign %s", storage_path, exc_info=True)
        return None
