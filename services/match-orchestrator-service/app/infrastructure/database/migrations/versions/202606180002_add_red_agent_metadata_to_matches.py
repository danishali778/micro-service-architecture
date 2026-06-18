"""add red agent metadata to matches

Revision ID: 202606180002
Revises: 202606170002
Create Date: 2026-06-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606180002"
down_revision: str | None = "202606170002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "matches", sa.Column("creation_request_hash", sa.String(length=128), nullable=True)
    )
    op.add_column("matches", sa.Column("red_run_id", sa.String(length=80), nullable=True))
    op.add_column("matches", sa.Column("red_run_state", sa.String(length=40), nullable=True))
    op.add_column("matches", sa.Column("red_agent_adapter", sa.String(length=80), nullable=True))
    op.add_column(
        "matches", sa.Column("red_agent_profile_ref", sa.String(length=160), nullable=True)
    )
    op.add_column("matches", sa.Column("attack_proposal_id", sa.String(length=80), nullable=True))
    op.add_column(
        "matches",
        sa.Column("attack_proposal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "attack_proposal")
    op.drop_column("matches", "attack_proposal_id")
    op.drop_column("matches", "red_agent_profile_ref")
    op.drop_column("matches", "red_agent_adapter")
    op.drop_column("matches", "red_run_state")
    op.drop_column("matches", "red_run_id")
    op.drop_column("matches", "creation_request_hash")
