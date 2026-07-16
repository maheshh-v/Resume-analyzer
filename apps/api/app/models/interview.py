from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk, utcnow


class Interview(Base, UUIDPk, TimestampMixin):
    __tablename__ = "interviews"

    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True, nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # status: pending | in_progress | submitted | expired
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Ordered claim targets frozen at invite time: [{claim_id, requirement_id, claim_text,
    # requirement_label}, ...]. Freezing this means later JD/claim edits never silently
    # reshape an interview that's already in progress.
    target_claims: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan", order_by="InterviewQuestion.ordinal"
    )


class InterviewQuestion(Base, UUIDPk, TimestampMixin):
    __tablename__ = "interview_questions"

    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    # depth 0 = base question for the claim; 1-3 = follow-up probes
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interview_questions.id"), nullable=True
    )
    targets_claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("claims.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_artifact_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # written BEFORE the answer exists: what a real practitioner would mention / what a bluffer would miss
    rubric: Mapped[dict] = mapped_column(JSON, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    interview: Mapped["Interview"] = relationship(back_populates="questions")
    answer: Mapped["InterviewAnswer | None"] = relationship(back_populates="question", uselist=False)


class InterviewAnswer(Base, UUIDPk, TimestampMixin):
    __tablename__ = "interview_answers"

    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_questions.id"), unique=True, index=True, nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    # specificity_verdict: strong | weak — drives the adaptive follow-up decision
    specificity_verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    specificity_notes: Mapped[str] = mapped_column(Text, nullable=False)
    time_to_first_keystroke_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paste_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # behavioral flags for human review only — never auto-reject, never a score
    review_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    question: Mapped["InterviewQuestion"] = relationship(back_populates="answer")
