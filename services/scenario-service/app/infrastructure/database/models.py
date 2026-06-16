from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ScenarioModel(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_tenant_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
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


class ScenarioVersionModel(Base):
    __tablename__ = "scenario_versions"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version", name="uq_scenario_versions_scenario_version"),
        Index("ix_scenario_versions_scenario_status", "scenario_id", "status"),
    )

    scenario_version_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    objectives: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    target_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    runtime_template: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    action_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    resource_budget: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    verification_contract: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
