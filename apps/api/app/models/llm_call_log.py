from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk


class LLMCallLog(Base, UUIDPk, TimestampMixin):
    """Per-call LLM cost + latency telemetry. Append-only, metadata ONLY.

    Deliberately stores no prompt or response bodies — a candidate's resume text and the model's
    reasoning never land in this table (privacy). It records just enough to answer "what did this
    candidate's verification cost, and where did the time/tokens go", and to reconcile against the
    Langfuse traces that carry the same tags.

    Not foreign-keyed to candidates on purpose: cost logging runs best-effort on its own session,
    independent of the pipeline transaction, and must never fail the pipeline or block a delete.
    """

    __tablename__ = "llm_call_log"

    candidate_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    pipeline_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
