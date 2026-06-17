from typing import Any, Protocol

from app.domain.entities.sandbox import (
    CleanupResult,
    ProviderAllocation,
    SandboxOperationResult,
    SandboxRecord,
    SandboxScenario,
)


class SandboxRepository(Protocol):
    def provision_sandbox(
        self,
        *,
        sandbox_id: str,
        tenant_id: str,
        subject_id: str,
        match_id: str,
        scenario: SandboxScenario,
        runtime_template: dict[str, Any],
        action_policy: dict[str, Any],
        resource_budget: dict[str, Any],
        lease_duration_seconds: int,
        provider_name: str,
        allocation: ProviderAllocation,
        idempotency_key: str,
        request_hash: str,
        retention_hours: int,
    ) -> SandboxOperationResult: ...

    def get_sandbox(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        sandbox_id: str,
    ) -> SandboxRecord | None: ...

    def terminate_sandbox(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        sandbox_id: str,
        reason: str,
        cleanup: CleanupResult,
        idempotency_key: str,
        request_hash: str,
        retention_hours: int,
    ) -> SandboxOperationResult: ...
