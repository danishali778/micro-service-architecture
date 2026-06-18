from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RedScenario:
    snapshot_id: str
    scenario_id: str
    version: str
    title: str

    def to_json(self) -> dict[str, str]:
        return {
            "snapshot_id": self.snapshot_id,
            "scenario_id": self.scenario_id,
            "version": self.version,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class AttackProposal:
    proposal_id: str
    proposal_type: str
    title: str
    summary: str
    rationale: str
    action: dict[str, Any]
    expected_signal: str
    risk_level: str
    confidence: float

    def to_json(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "title": self.title,
            "summary": self.summary,
            "rationale": self.rationale,
            "action": self.action,
            "expected_signal": self.expected_signal,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class AgentInfo:
    adapter: str
    profile_ref: str

    def to_json(self) -> dict[str, str]:
        return {"adapter": self.adapter, "profile_ref": self.profile_ref}


@dataclass(frozen=True, slots=True)
class RedRunRequest:
    match_id: str
    sandbox_id: str
    scenario: RedScenario
    target_profile: dict[str, Any]
    action_policy: dict[str, Any]
    resource_budget: dict[str, Any]
    agent_profile_ref: str


@dataclass(frozen=True, slots=True)
class RedRunRecord:
    id: str
    tenant_id: str
    subject_id: str
    match_id: str
    sandbox_id: str
    scenario: RedScenario
    state: str
    status_reason: str
    agent: AgentInfo
    proposal: AttackProposal | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    failed_at: datetime | None


@dataclass(frozen=True, slots=True)
class RedRunOperationResult:
    red_run: RedRunRecord
    status_code: int
