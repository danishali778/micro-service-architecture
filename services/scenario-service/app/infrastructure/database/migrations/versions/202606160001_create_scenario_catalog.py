"""create scenario catalog

Revision ID: 202606160001
Revises:
Create Date: 2026-06-16 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606160001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("scenario_id", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("owner_tenant_id", sa.String(length=120), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("scenario_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "scenario_versions",
        sa.Column("scenario_version_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_id", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("objectives", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("runtime_template", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resource_budget", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_contract", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("scenario_version_id"),
        sa.UniqueConstraint("scenario_id", "version", name="uq_scenario_versions_scenario_version"),
    )
    op.create_index(
        "ix_scenario_versions_scenario_status",
        "scenario_versions",
        ["scenario_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_versions_scenario_status", table_name="scenario_versions")
    op.drop_table("scenario_versions")
    op.drop_table("scenarios")
