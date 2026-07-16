from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk


class Claim(Base, UUIDPk, TimestampMixin):
    __tablename__ = "claims"

    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True, nullable=False)
    # claim_type: skill | employment | education | project | credential
    claim_type: Mapped[str] = mapped_column(String(20), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_skill: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    asserted_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    asserted_start: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ISO-ish "YYYY-MM"
    asserted_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    asserted_org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # MUST resolve as a literal substring of documents.extracted_text[start:end] — enforced in pipeline, not DB.
    source_span_start: Mapped[int] = mapped_column(Integer, nullable=False)
    source_span_end: Mapped[int] = mapped_column(Integer, nullable=False)
    extractor_model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="claims")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
