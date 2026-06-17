from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class SandboxModel(Base):
    __tablename__ = "sandboxes"
    __table_args__ = (
        Index("ix_sandboxes_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_sandboxes_tenant_match", "tenant_id", "match_id"),
        Index("ix_sandboxes_tenant_state", "tenant_id", "state"),
    )

    sandbox_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    match_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_snapshot_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    status_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    runtime_template: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    action_policy: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    resource_budget: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    allocation: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    cleanup: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT, nullable=True)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SandboxAttemptModel(Base):
    __tablename__ = "sandbox_attempts"
    __table_args__ = (
        UniqueConstraint(
            "sandbox_id",
            "attempt_type",
            "attempt_number",
            name="uq_sandbox_attempt_number",
        ),
    )

    sandbox_attempt_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    sandbox_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("sandboxes.sandbox_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_type: Mapped[str] = mapped_column(String(40), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    state_before: Mapped[str] = mapped_column(String(40), nullable=False)
    state_after: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    status_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    safe_details: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SandboxTransitionModel(Base):
    __tablename__ = "sandbox_transitions"
    __table_args__ = (
        Index("ix_sandbox_transitions_sandbox_version", "sandbox_id", "aggregate_version"),
    )

    sandbox_transition_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    sandbox_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("sandboxes.sandbox_id", ondelete="CASCADE"),
        nullable=False,
    )
    from_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_state: Mapped[str] = mapped_column(String(40), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    caused_by_type: Mapped[str] = mapped_column(String(40), nullable=False)
    caused_by_id: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_workload_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "subject_id",
            "route",
            "idempotency_key",
            name="uq_sandbox_idempotency_scope_key",
        ),
    )

    idempotency_record_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    route: Mapped[str] = mapped_column(String(160), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class OutboxRecordModel(Base):
    __tablename__ = "outbox_records"

    outbox_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    message_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
