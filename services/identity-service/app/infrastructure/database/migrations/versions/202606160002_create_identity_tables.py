"""create identity tables

Revision ID: 202606160002
Revises:
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606160002"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("supabase_user_id", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("supabase_user_id"),
    )
    op.create_table(
        "roles",
        sa.Column("role_code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("role_code"),
    )
    op.create_table(
        "scopes",
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("scope"),
    )
    op.create_table(
        "service_accounts",
        sa.Column("service_account_id", sa.String(length=120), nullable=False),
        sa.Column("workload_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("allowed_scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("service_account_id"),
        sa.UniqueConstraint("workload_id"),
    )
    op.create_table(
        "memberships",
        sa.Column("membership_id", sa.String(length=120), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("membership_id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),
    )
    op.create_index(
        "ix_memberships_user_status",
        "memberships",
        ["user_id", "status"],
    )
    op.create_table(
        "role_scopes",
        sa.Column("role_scope_id", sa.String(length=120), nullable=False),
        sa.Column("role_code", sa.String(length=80), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["role_code"], ["roles.role_code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scope"], ["scopes.scope"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_scope_id"),
        sa.UniqueConstraint("role_code", "scope", name="uq_role_scopes_role_scope"),
    )
    op.create_table(
        "role_assignments",
        sa.Column("role_assignment_id", sa.String(length=120), nullable=False),
        sa.Column("membership_id", sa.String(length=120), nullable=False),
        sa.Column("role_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["memberships.membership_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["role_code"], ["roles.role_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_assignment_id"),
        sa.UniqueConstraint(
            "membership_id",
            "role_code",
            name="uq_role_assignments_membership_role",
        ),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("auth_session_id", sa.String(length=120), nullable=False),
        sa.Column("supabase_user_id", sa.String(length=120), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("auth_session_id"),
    )
    op.create_index(
        "ix_auth_sessions_supabase_user_session",
        "auth_sessions",
        ["supabase_user_id", "session_id"],
    )
    op.create_table(
        "authorization_audit",
        sa.Column("audit_id", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("workload_id", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=True),
        sa.Column("resource_id", sa.String(length=160), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("correlation_id", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        "ix_authorization_audit_subject_tenant",
        "authorization_audit",
        ["subject_id", "tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_authorization_audit_subject_tenant", table_name="authorization_audit")
    op.drop_table("authorization_audit")
    op.drop_index("ix_auth_sessions_supabase_user_session", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("role_assignments")
    op.drop_table("role_scopes")
    op.drop_index("ix_memberships_user_status", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("service_accounts")
    op.drop_table("scopes")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("tenants")
