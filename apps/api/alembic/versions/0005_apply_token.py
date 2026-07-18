"""public apply-link token on jobs

Revision ID: 0005_apply_token
Revises: 0004_public_api
Create Date: 2026-07-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_apply_token"
down_revision: Union[str, None] = "0004_public_api"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("apply_token", sa.String(64), nullable=True))
    op.create_index("ix_jobs_apply_token", "jobs", ["apply_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_jobs_apply_token", table_name="jobs")
    op.drop_column("jobs", "apply_token")
