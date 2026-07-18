from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk


class PublicReport(Base, UUIDPk, TimestampMixin):
    """A verification requested through the white-label API. `id` is the report_id handed back to
    the caller. The verification runs asynchronously; `status` moves pending -> processing ->
    ready|failed. Scoped to the creating API key — only that key may read it back."""

    __tablename__ = "public_reports"

    api_key_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_keys.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pdf_storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
