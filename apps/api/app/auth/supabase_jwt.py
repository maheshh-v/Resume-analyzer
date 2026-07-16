"""Verifies Supabase-issued JWTs against the project's JWKS endpoint.

The browser authenticates with Supabase directly and never touches app data or Storage —
it only ever sends this JWT to FastAPI, which is the sole thing that talks to Postgres
and Storage. See docs/ARCHITECTURE.md section 2 for the full security model.
"""

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from app.config import get_settings


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class SupabasePrincipal:
    auth_id: str
    email: str


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    settings = get_settings()
    if not settings.supabase_jwks_url:
        raise TokenError("SUPABASE_JWKS_URL is not configured")
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.supabase_jwks_url)
    return _jwks_client


def decode_supabase_jwt(token: str) -> SupabasePrincipal:
    """Verify signature + expiry via the project's JWKS, then extract identity claims.

    Raises TokenError on any failure (expired, bad signature, missing claims) so callers
    can uniformly turn it into a 401 without leaking which check failed.
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except Exception as exc:  # jwt.* exceptions + JWKS lookup errors
        raise TokenError(str(exc)) from exc

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise TokenError("token missing sub/email claims")
    return SupabasePrincipal(auth_id=sub, email=email)
