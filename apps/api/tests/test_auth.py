from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

import app.auth.supabase_jwt as supabase_jwt_module
from app.auth.dependencies import get_current_user
from app.auth.supabase_jwt import TokenError, decode_supabase_jwt
from app.models.user import User

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKSClient:
    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(_PRIVATE_KEY.public_key())


@pytest.fixture(autouse=True)
def _patch_jwks_client(monkeypatch):
    monkeypatch.setattr(supabase_jwt_module, "_get_jwks_client", lambda: _FakeJWKSClient())
    yield


def _make_token(*, sub="user-123", email="candidate@example.com", exp_delta=timedelta(hours=1), aud="authenticated"):
    payload = {"sub": sub, "email": email, "aud": aud, "exp": datetime.now(timezone.utc) + exp_delta}
    return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")


def test_decode_valid_token_returns_principal():
    token = _make_token()
    principal = decode_supabase_jwt(token)
    assert principal.auth_id == "user-123"
    assert principal.email == "candidate@example.com"


def test_decode_expired_token_raises():
    token = _make_token(exp_delta=timedelta(hours=-1))
    with pytest.raises(TokenError):
        decode_supabase_jwt(token)


def test_decode_wrong_audience_raises():
    token = _make_token(aud="not-authenticated")
    with pytest.raises(TokenError):
        decode_supabase_jwt(token)


def test_decode_missing_email_raises():
    payload = {"sub": "user-123", "aud": "authenticated", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")
    with pytest.raises(TokenError):
        decode_supabase_jwt(token)


@pytest.mark.asyncio
async def test_get_current_user_creates_local_row_on_first_sight(db_session):
    from fastapi.security import HTTPAuthorizationCredentials

    token = _make_token(sub="brand-new-auth-id", email="new@example.com")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = await get_current_user(credentials=creds, db=db_session)
    assert user.auth_id == "brand-new-auth-id"
    assert user.email == "new@example.com"

    result = await db_session.execute(select(User).where(User.auth_id == "brand-new-auth-id"))
    assert result.scalar_one() is not None


@pytest.mark.asyncio
async def test_get_current_user_reuses_existing_row(db_session):
    from fastapi.security import HTTPAuthorizationCredentials

    existing = User(auth_id="existing-auth-id", email="existing@example.com")
    db_session.add(existing)
    await db_session.commit()

    token = _make_token(sub="existing-auth-id", email="existing@example.com")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(credentials=creds, db=db_session)

    assert user.id == existing.id


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_credentials(db_session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=db_session)
    assert exc_info.value.status_code == 401
