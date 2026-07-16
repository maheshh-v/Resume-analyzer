from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.supabase_jwt import TokenError, decode_supabase_jwt
from app.db.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verifies the Supabase JWT and returns the local `users` row, creating it on first sight.

    This is the ONLY place identity is established. Every router that needs auth depends on
    this, and every query a router makes must then filter by `current_user.id` — see
    docs/ARCHITECTURE.md section 2. There is no separate "is this mine" check scattered
    elsewhere; ownership is enforced by always querying through owner_user_id.
    """
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        principal = decode_supabase_jwt(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    result = await db.execute(select(User).where(User.auth_id == principal.auth_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(auth_id=principal.auth_id, email=principal.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
