from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk


class Document(Base, UUIDPk, TimestampMixin):
    __tablename__ = "documents"

    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="resume", nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    # per-page character offsets into extracted_text, e.g. [[0,1200],[1200,2400]]
    page_offsets: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="documents")
