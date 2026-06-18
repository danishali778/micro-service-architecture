"""create red agent tables

Revision ID: 202606180001
Revises:
Create Date: 2026-06-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606180001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "red_runs",
        sa.Column("red_run_id", sa.String(length=80), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("sandbox_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_snapshot_id", sa.String(length=120), nullable=False),
        sa.Column("scenario_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_version", sa.String(length=32), nullable=False),
        sa.Column("scenario", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resource_budget", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("agent_adapter", sa.String(length=80), nullable=False),
        sa.Column("agent_profile_ref", sa.String(length=160), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("status_reason", sa.String(length=120), nullable=False),
        sa.Column("proposal_id", sa.String(length=80), nullable=True),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("red_run_id"),
    )
    op.create_index("ix_red_runs_tenant_match", "red_runs", ["tenant_id", "match_id"])
    op.create_index("ix_red_runs_tenant_state", "red_runs", ["tenant_id", "state"])
    op.create_table(
        "red_run_attempts",
        sa.Column("red_run_attempt_id", sa.String(length=80), nullable=False),
        sa.Column("red_run_id", sa.String(length=80), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("adapter", sa.String(length=80), nullable=False),
        sa.Column("profile_ref", sa.String(length=160), nullable=False),
        sa.Column("state_before", sa.String(length=40), nullable=False),
        sa.Column("state_after", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("status_reason", sa.String(length=120), nullable=False),
        sa.Column("safe_details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["red_run_id"], ["red_runs.red_run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("red_run_attempt_id"),
    )
    op.create_table(
        "attack_proposals",
        sa.Column("proposal_id", sa.String(length=80), nullable=False),
        sa.Column("red_run_id", sa.String(length=80), nullable=False),
        sa.Column("proposal_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_signal", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("validation_status", sa.String(length=40), nullable=False),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["red_run_id"], ["red_runs.red_run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("proposal_id"),
    )
    op.create_table(
        "red_run_transitions",
        sa.Column("red_run_transition_id", sa.String(length=80), nullable=False),
        sa.Column("red_run_id", sa.String(length=80), nullable=False),
        sa.Column("from_state", sa.String(length=40), nullable=True),
        sa.Column("to_state", sa.String(length=40), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("actor_workload_id", sa.String(length=120), nullable=False),
        sa.Column("actor_subject_id", sa.String(length=120), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["red_run_id"], ["red_runs.red_run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("red_run_transition_id"),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("idempotency_record_id", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("route", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_record_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "subject_id",
            "route",
            "idempotency_key",
            name="uq_red_idempotency_scope_key",
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("outbox_id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(
        "ix_red_outbox_status_available",
        "outbox_records",
        ["status", "available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_red_outbox_status_available", table_name="outbox_records")
    op.drop_table("outbox_records")
    op.drop_table("idempotency_records")
    op.drop_table("red_run_transitions")
    op.drop_table("attack_proposals")
    op.drop_table("red_run_attempts")
    op.drop_index("ix_red_runs_tenant_state", table_name="red_runs")
    op.drop_index("ix_red_runs_tenant_match", table_name="red_runs")
    op.drop_table("red_runs")
