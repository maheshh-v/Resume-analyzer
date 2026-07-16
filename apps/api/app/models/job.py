from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk


class Job(Base, UUIDPk, TimestampMixin):
    __tablename__ = "jobs"

    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    jd_raw: Mapped[str] = mapped_column(Text, nullable=False)
    # requirements_status: draft (auto-extracted, awaiting recruiter review) | reviewed
    requirements_status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)

    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="JobRequirement.ordinal"
    )
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobRequirement(Base, UUIDPk, TimestampMixin):
    __tablename__ = "job_requirements"

    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skill: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_skill: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="technical", nullable=False)
    # importance: must_have | nice_to_have
    importance: Mapped[str] = mapped_column(String(20), default="nice_to_have", nullable=False)
    min_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    # what evidence would actually satisfy this claim — the spec for the evidence hunt
    evidence_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    source_span_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_span_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="requirements")
