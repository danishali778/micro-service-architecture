"""create sandbox tables

Revision ID: 202606170001
Revises: None
Create Date: 2026-06-17 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeEngine

revision: str = "202606170001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    json_type = _json_type()
    op.create_table(
        "sandboxes",
        sa.Column("sandbox_id", sa.String(length=80), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_snapshot_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_version", sa.String(length=32), nullable=False),
        sa.Column("scenario", json_type, nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("status_reason", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("runtime_template", json_type, nullable=False),
        sa.Column("action_policy", json_type, nullable=False),
        sa.Column("resource_budget", json_type, nullable=False),
        sa.Column("allocation", json_type, nullable=False),
        sa.Column("cleanup", json_type, nullable=True),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("sandbox_id"),
    )
    op.create_index("ix_sandboxes_tenant_match", "sandboxes", ["tenant_id", "match_id"])
    op.create_index("ix_sandboxes_tenant_state", "sandboxes", ["tenant_id", "state"])
    op.create_index("ix_sandboxes_tenant_subject", "sandboxes", ["tenant_id", "subject_id"])
    op.create_table(
        "sandbox_attempts",
        sa.Column("sandbox_attempt_id", sa.String(length=80), nullable=False),
        sa.Column("sandbox_id", sa.String(length=80), nullable=False),
        sa.Column("attempt_type", sa.String(length=40), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("state_before", sa.String(length=40), nullable=False),
        sa.Column("state_after", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("status_reason", sa.String(length=200), nullable=False),
        sa.Column("safe_details", json_type, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sandbox_id"], ["sandboxes.sandbox_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sandbox_attempt_id"),
        sa.UniqueConstraint(
            "sandbox_id",
            "attempt_type",
            "attempt_number",
            name="uq_sandbox_attempt_number",
        ),
    )
    op.create_table(
        "sandbox_transitions",
        sa.Column("sandbox_transition_id", sa.String(length=80), nullable=False),
        sa.Column("sandbox_id", sa.String(length=80), nullable=False),
        sa.Column("from_state", sa.String(length=40), nullable=True),
        sa.Column("to_state", sa.String(length=40), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("caused_by_type", sa.String(length=40), nullable=False),
        sa.Column("caused_by_id", sa.String(length=160), nullable=False),
        sa.Column("actor_workload_id", sa.String(length=120), nullable=False),
        sa.Column("actor_subject_id", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sandbox_id"], ["sandboxes.sandbox_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sandbox_transition_id"),
    )
    op.create_index(
        "ix_sandbox_transitions_sandbox_version",
        "sandbox_transitions",
        ["sandbox_id", "aggregate_version"],
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
        sa.Column("response_body", json_type, nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_record_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "subject_id",
            "route",
            "idempotency_key",
            name="uq_sandbox_idempotency_scope_key",
        ),
    )
    op.create_table(
        "outbox_records",
        sa.Column("outbox_id", sa.String(length=80), nullable=False),
        sa.Column("message_id", sa.String(length=80), nullable=False),
        sa.Column("message_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_id", sa.String(length=80), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("outbox_id"),
        sa.UniqueConstraint("message_id"),
    )


def downgrade() -> None:
    op.drop_table("outbox_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_sandbox_transitions_sandbox_version", table_name="sandbox_transitions")
    op.drop_table("sandbox_transitions")
    op.drop_table("sandbox_attempts")
    op.drop_index("ix_sandboxes_tenant_subject", table_name="sandboxes")
    op.drop_index("ix_sandboxes_tenant_state", table_name="sandboxes")
    op.drop_index("ix_sandboxes_tenant_match", table_name="sandboxes")
    op.drop_table("sandboxes")
