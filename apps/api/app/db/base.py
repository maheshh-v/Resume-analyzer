import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Postgres (asyncpg) round-trips DateTime(timezone=True) as tz-aware; SQLite has no
    native tz-aware timestamp type and hands back a naive datetime instead. We only ever
    write UTC, so a naive value read back is always safe to treat as UTC. Comparisons against
    a fresh `datetime.now(timezone.utc)` must go through this or they raise on SQLite."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class UUIDPk:
    """Portable primary key: string UUID works identically on SQLite (tests) and Postgres (prod)."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
