from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk


class Evidence(Base, UUIDPk, TimestampMixin):
    """Append-only. Never updated, never deleted — lets us reconstruct what the system knew at any moment.

    A row may only ever be written after citation validation passes (source span / artifact_url
    resolve). Confidence is for internal calibration only and must never be surfaced as a score.
    """

    __tablename__ = "evidence"

    claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("claims.id"), index=True, nullable=False)
    # source_type: consistency | github | interview | semantic_scholar | google_patents | package_ownership
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # verdict: verified | partial | unverified | contradicted
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    artifact_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="evidence")
