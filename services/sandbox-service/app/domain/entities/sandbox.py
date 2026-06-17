from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SandboxScenario:
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
class ProviderAllocation:
    allocation_id: str
    metadata: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {"allocation_id": self.allocation_id, **self.metadata}


@dataclass(frozen=True, slots=True)
class CleanupResult:
    status: str
    details: list[dict[str, Any]]

    def to_json(self) -> dict[str, Any]:
        return {"status": self.status, "details": self.details}


@dataclass(frozen=True, slots=True)
class SandboxRecord:
    id: str
    tenant_id: str
    subject_id: str
    match_id: str
    scenario: SandboxScenario
    state: str
    status_reason: str
    provider: str
    allocation: dict[str, Any]
    lease_expires_at: datetime
    created_at: datetime
    updated_at: datetime
    ready_at: datetime | None
    terminated_at: datetime | None
    failed_at: datetime | None
    cleanup: CleanupResult | None = None


@dataclass(frozen=True, slots=True)
class SandboxOperationResult:
    sandbox: SandboxRecord
    status_code: int
