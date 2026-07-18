"""llm call log (cost + latency telemetry, metadata only)

Revision ID: 0003_llm_call_log
Revises: 0002_ledger
Create Date: 2026-07-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_llm_call_log"
down_revision: Union[str, None] = "0002_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.String(36), primary_key=True),
        # Not FK-constrained on purpose: cost logging runs best-effort on its own session and
        # must never fail the pipeline or block a candidate delete.
        sa.Column("candidate_id", sa.String(36), nullable=True),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("pipeline_stage", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(20), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_call_log_candidate_id", "llm_call_log", ["candidate_id"])
    op.create_index("ix_llm_call_log_job_id", "llm_call_log", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_log_job_id", table_name="llm_call_log")
    op.drop_index("ix_llm_call_log_candidate_id", table_name="llm_call_log")
    op.drop_table("llm_call_log")
