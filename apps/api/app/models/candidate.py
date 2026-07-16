from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk


class Candidate(Base, UUIDPk, TimestampMixin):
    __tablename__ = "candidates"

    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    github_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # status: pending | processing | ready | failed — drives frontend polling after upload
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    status_detail: Mapped[str | None] = mapped_column(String(512), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="candidates")
    documents: Mapped[list["Document"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    claims: Mapped[list["Claim"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
