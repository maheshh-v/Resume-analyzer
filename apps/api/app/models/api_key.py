from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk


class ApiKey(Base, UUIDPk, TimestampMixin):
    """A white-label API credential for a staffing agency.

    Only the SHA-256 of the raw key is stored — the plaintext is shown once, at creation, and
    never again (see app/cli.py). `key_prefix` is a non-secret display fragment for dashboards.
    `monthly_quota` of 0 means unlimited. `stripe_customer_id` opts the org into metered billing;
    `logo_url` fills the org-logo slot on the branded PDF.
    """

    __tablename__ = "api_keys"

    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    @property
    def quota_exhausted(self) -> bool:
        return self.monthly_quota > 0 and self.usage_count >= self.monthly_quota
