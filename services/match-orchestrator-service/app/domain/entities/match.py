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
    sandbox_id: str | None
    sandbox_state: str | None
    sandbox_provider: str | None
    sandbox_allocation: dict[str, Any] | None
    red_run_id: str | None
    red_run_state: str | None
    red_agent_adapter: str | None
    red_agent_profile_ref: str | None
    attack_proposal_id: str | None
    attack_proposal: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class SandboxProvision:
    id: str
    state: str
    provider: str
    allocation: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RedRunProposal:
    id: str
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
            "proposal_id": self.id,
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
class RedRunResult:
    id: str
    state: str
    adapter: str
    profile_ref: str
    proposal: RedRunProposal


@dataclass(frozen=True, slots=True)
class MatchOperationResult:
    match: MatchRecord
    status_code: int
