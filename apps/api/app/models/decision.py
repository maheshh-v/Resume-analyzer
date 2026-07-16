from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk


class Decision(Base, UUIDPk, TimestampMixin):
    """The only verdict that exists in the system. A human made it; we record who, when, why."""

    __tablename__ = "decisions"

    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True, nullable=False)
    decided_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # verdict: advance | hold | decline
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
