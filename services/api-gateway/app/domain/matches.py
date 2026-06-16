from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MatchScenario:
    id: str
    version: str
    snapshot_id: str
    title: str


@dataclass(frozen=True, slots=True)
class Match:
    id: str
    tenant_id: str
    subject_id: str
    scenario: MatchScenario
    state: str
    phase: str
    status_reason: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
