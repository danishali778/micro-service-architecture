from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ScenarioSnapshot:
    snapshot_id: str
    scenario_id: str
    version: str
    title: str
    target_profile: dict[str, Any]
    runtime_template: dict[str, Any]
    action_policy: dict[str, Any]
    resource_budget: dict[str, Any]
    verification_contract: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "scenario_id": self.scenario_id,
            "version": self.version,
            "title": self.title,
            "target_profile": self.target_profile,
            "runtime_template": self.runtime_template,
            "action_policy": self.action_policy,
            "resource_budget": self.resource_budget,
            "verification_contract": self.verification_contract,
        }


@dataclass(frozen=True, slots=True)
class MatchRecord:
    id: str
    tenant_id: str
    subject_id: str
    scenario: ScenarioSnapshot
    state: str
    phase: str
    status_reason: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None


@dataclass(frozen=True, slots=True)
class MatchOperationResult:
    match: MatchRecord
    status_code: int
