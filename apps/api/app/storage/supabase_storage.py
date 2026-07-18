"""Thin wrapper over the Supabase Storage REST API.

FastAPI is the only thing that touches Storage (see docs/ARCHITECTURE.md section 2) — the
browser never gets a Storage credential. Uses the service role key over HTTPS; no Supabase
SDK dependency needed for this one call shape.
"""

import httpx

from app.config import get_settings


class StorageError(Exception):
    pass


async def upload_resume(*, candidate_id: str, filename: str, content: bytes) -> str:
    """Uploads to `{bucket}/{candidate_id}/{filename}` and returns the storage path
    (not a public URL — resumes are private; fetch via a signed URL or the service key)."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured")

    storage_path = f"{candidate_id}/{filename}"
    url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/pdf",
        "x-upsert": "true",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, content=content)
    if response.status_code >= 400:
        raise StorageError(f"Supabase Storage upload failed ({response.status_code}): {response.text}")
    return storage_path


async def upload_object(
    *,
    bucket: str,
    path: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    client: httpx.AsyncClient | None = None,
) -> str:
    """Upload bytes to `{bucket}/{path}` (upsert) and return the bucket-relative path. Used for the
    branded report PDFs (a different bucket than resumes). `client` is injectable for tests."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured")

    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    if client is not None:
        response = await client.post(url, headers=headers, content=content)
    else:
        async with httpx.AsyncClient(timeout=30) as owned:
            response = await owned.post(url, headers=headers, content=content)
    if response.status_code >= 400:
        raise StorageError(f"Supabase Storage upload failed ({response.status_code}): {response.text}")
    return path


async def create_signed_url(
    storage_path: str,
    *,
    bucket: str | None = None,
    expires_in: int = 3600,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Return a time-limited signed URL for a private object (e.g. a branded report PDF).

    `storage_path` is bucket-relative. `bucket` defaults to the resumes bucket for back-compat.
    Raises StorageError if Storage isn't configured or the sign call fails."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured")
    bucket = bucket or settings.supabase_storage_bucket

    url = f"{settings.supabase_url}/storage/v1/object/sign/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    if client is not None:
        response = await client.post(url, headers=headers, json={"expiresIn": expires_in})
    else:
        async with httpx.AsyncClient(timeout=15) as owned:
            response = await owned.post(url, headers=headers, json={"expiresIn": expires_in})
    if response.status_code >= 400:
        raise StorageError(f"Supabase Storage sign failed ({response.status_code}): {response.text}")
    signed = response.json().get("signedURL", "")
    return f"{settings.supabase_url}/storage/v1{signed}"
