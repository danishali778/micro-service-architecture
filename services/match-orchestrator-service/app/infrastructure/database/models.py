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


class MatchModel(Base):
    __tablename__ = "matches"
    __table_args__ = (
        Index("ix_matches_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_matches_tenant_state", "tenant_id", "state"),
    )

    match_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(120), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_snapshot_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    sandbox_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sandbox_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sandbox_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sandbox_allocation: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT, nullable=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    phase: Mapped[str] = mapped_column(String(40), nullable=False)
    status_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatchAttemptModel(Base):
    __tablename__ = "match_attempts"
    __table_args__ = (
        UniqueConstraint("match_id", "attempt_number", name="uq_match_attempt_number"),
    )

    match_attempt_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    match_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("matches.match_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminal_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class MatchTransitionModel(Base):
    __tablename__ = "match_transitions"
    __table_args__ = (Index("ix_match_transitions_match_version", "match_id", "aggregate_version"),)

    transition_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    match_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("matches.match_id", ondelete="CASCADE"),
        nullable=False,
    )
    from_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_state: Mapped[str] = mapped_column(String(40), nullable=False)
    from_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_phase: Mapped[str] = mapped_column(String(40), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    caused_by_type: Mapped[str] = mapped_column(String(40), nullable=False)
    caused_by_id: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
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
            name="uq_idempotency_scope_key",
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
