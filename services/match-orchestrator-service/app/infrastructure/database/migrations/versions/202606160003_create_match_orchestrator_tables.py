"""create match orchestrator tables

Revision ID: 202606160003
Revises:
Create Date: 2026-06-16 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606160003"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("scenario_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_version", sa.String(length=32), nullable=False),
        sa.Column("scenario_snapshot_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("phase", sa.String(length=40), nullable=False),
        sa.Column("status_reason", sa.String(length=200), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
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
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("match_id"),
    )
    op.create_index("ix_matches_tenant_state", "matches", ["tenant_id", "state"])
    op.create_index("ix_matches_tenant_subject", "matches", ["tenant_id", "subject_id"])

    op.create_table(
        "match_attempts",
        sa.Column("match_attempt_id", sa.String(length=80), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_state", sa.String(length=40), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.match_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("match_attempt_id"),
        sa.UniqueConstraint("match_id", "attempt_number", name="uq_match_attempt_number"),
    )

    op.create_table(
        "match_transitions",
        sa.Column("transition_id", sa.String(length=80), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("from_state", sa.String(length=40), nullable=True),
        sa.Column("to_state", sa.String(length=40), nullable=False),
        sa.Column("from_phase", sa.String(length=40), nullable=True),
        sa.Column("to_phase", sa.String(length=40), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("caused_by_type", sa.String(length=40), nullable=False),
        sa.Column("caused_by_id", sa.String(length=160), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["matches.match_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("transition_id"),
    )
    op.create_index(
        "ix_match_transitions_match_version",
        "match_transitions",
        ["match_id", "aggregate_version"],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("idempotency_record_id", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("route", sa.String(length=160), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("idempotency_record_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "subject_id",
            "route",
            "idempotency_key",
            name="uq_idempotency_scope_key",
        ),
    )

    op.create_table(
        "outbox_records",
        sa.Column("outbox_id", sa.String(length=80), nullable=False),
        sa.Column("message_id", sa.String(length=80), nullable=False),
        sa.Column("message_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_id", sa.String(length=80), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("outbox_id"),
        sa.UniqueConstraint("message_id"),
    )


def downgrade() -> None:
    op.drop_table("outbox_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_match_transitions_match_version", table_name="match_transitions")
    op.drop_table("match_transitions")
    op.drop_table("match_attempts")
    op.drop_index("ix_matches_tenant_subject", table_name="matches")
    op.drop_index("ix_matches_tenant_state", table_name="matches")
    op.drop_table("matches")
