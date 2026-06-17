"""add sandbox metadata to matches

Revision ID: 202606170002
Revises: 202606160003
Create Date: 2026-06-17 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeEngine

revision: str = "202606170002"
down_revision: str | None = "202606160003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("matches", sa.Column("sandbox_id", sa.String(length=80), nullable=True))
    op.add_column("matches", sa.Column("sandbox_state", sa.String(length=40), nullable=True))
    op.add_column("matches", sa.Column("sandbox_provider", sa.String(length=80), nullable=True))
    op.add_column("matches", sa.Column("sandbox_allocation", _json_type(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "sandbox_allocation")
    op.drop_column("matches", "sandbox_provider")
    op.drop_column("matches", "sandbox_state")
    op.drop_column("matches", "sandbox_id")
