"""API-key authentication dependency for the public surface.

Accepts the key via `Authorization: Bearer <key>` or `X-API-Key: <key>`. Looks it up by hash,
rejects unknown (401) and revoked (403) keys. Quota is enforced at the call site (verify) so a
read like GET /reports never consumes quota.
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.api_key import ApiKey
from app.public_api.keys import hash_api_key


def _extract_key(authorization: str | None, x_api_key: str | None) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


async def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    raw = _extract_key(authorization, x_api_key)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    key = (
        await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw)))
    ).scalar_one_or_none()
    if key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    if not key.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key has been revoked")
    return key
