from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk


class User(Base, UUIDPk, TimestampMixin):
    """Mirrors the Supabase-authenticated user. auth_id is the Supabase auth.users UUID (JWT `sub`)."""

    __tablename__ = "users"

    auth_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
