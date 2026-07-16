from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk

GENESIS_HASH = "0" * 64


class LedgerEvent(Base, UUIDPk, TimestampMixin):
    """One link in a candidate's tamper-evident verification chain.

    Append-only, per-candidate hash chain: event_hash = SHA-256 over the event's canonical
    serialization including prev_hash, so no event can be altered, inserted, or removed after
    the fact without breaking every hash downstream of it. Free text (answers, rationales) is
    stored elsewhere and referenced here by content hash — editing the underlying row later is
    detectable by re-hashing. Never write rows directly; go through app.ledger.append_event so
    seq/prev_hash/event_hash stay consistent.
    """

    __tablename__ = "ledger_events"
    # A seq collision means two writers raced to extend the same chain — fail loudly rather
    # than fork it.
    __table_args__ = (UniqueConstraint("candidate_id", "seq", name="uq_ledger_candidate_seq"),)

    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    # e.g. candidate_created | resume_ingested | claims_extracted | consistency_checked |
    # github_evidence | interview_created | question_asked | answer_recorded |
    # interview_submitted | decision_recorded
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # actor_type: human (recruiter) | candidate | model | system
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
