from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class RedRunModel(Base):
    __tablename__ = "red_runs"
    __table_args__ = (
        Index("ix_red_runs_tenant_match", "tenant_id", "match_id"),
        Index("ix_red_runs_tenant_state", "tenant_id", "state"),
    )

    red_run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    match_id: Mapped[str] = mapped_column(String(80), nullable=False)
    sandbox_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_snapshot_id: Mapped[str] = mapped_column(String(120), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    target_profile: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    action_policy: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    resource_budget: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    agent_adapter: Mapped[str] = mapped_column(String(80), nullable=False)
    agent_profile_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    status_reason: Mapped[str] = mapped_column(String(120), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RedRunAttemptModel(Base):
    __tablename__ = "red_run_attempts"

    red_run_attempt_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    red_run_id: Mapped[str] = mapped_column(
        ForeignKey("red_runs.red_run_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    adapter: Mapped[str] = mapped_column(String(80), nullable=False)
    profile_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    state_before: Mapped[str] = mapped_column(String(40), nullable=False)
    state_after: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    status_reason: Mapped[str] = mapped_column(String(120), nullable=False)
    safe_details: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AttackProposalModel(Base):
    __tablename__ = "attack_proposals"

    proposal_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    red_run_id: Mapped[str] = mapped_column(
        ForeignKey("red_runs.red_run_id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    expected_signal: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(40), nullable=False)
    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RedRunTransitionModel(Base):
    __tablename__ = "red_run_transitions"

    red_run_transition_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    red_run_id: Mapped[str] = mapped_column(
        ForeignKey("red_runs.red_run_id", ondelete="CASCADE"),
        nullable=False,
    )
    from_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_state: Mapped[str] = mapped_column(String(40), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_workload_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "subject_id",
            "route",
            "idempotency_key",
            name="uq_red_idempotency_scope_key",
        ),
    )

    idempotency_record_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    route: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxRecordModel(Base):
    __tablename__ = "outbox_records"
    __table_args__ = (Index("ix_red_outbox_status_available", "status", "available_at"),)

    outbox_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    message_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
