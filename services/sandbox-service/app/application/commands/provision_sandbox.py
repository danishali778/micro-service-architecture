from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from typing import Any
from uuid import uuid4

from app.application.ports.provider import SandboxProvider
from app.application.ports.sandbox_repository import SandboxRepository
from app.core.config import Settings
from app.core.exceptions import ValidationFailedError
from app.domain.entities.sandbox import SandboxOperationResult, SandboxScenario
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class ProvisionSandbox:
    repository: SandboxRepository
    provider: SandboxProvider
    settings: Settings

    def execute(
        self,
        *,
        match_id: str,
        scenario: SandboxScenario,
        runtime_template: dict[str, Any],
        action_policy: dict[str, Any],
        resource_budget: dict[str, Any],
        lease_duration_seconds: int | None,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxOperationResult:
        resolved_lease = lease_duration_seconds or self.settings.default_lease_seconds
        if resolved_lease > self.settings.max_lease_seconds:
            raise ValidationFailedError(
                "The requested lease exceeds the maximum allowed duration.",
                details=[
                    {
                        "loc": ["body", "lease_duration_seconds"],
                        "msg": "lease exceeds maximum",
                    }
                ],
            )

        request_hash = _request_hash(
            {
                "operation": "provision_sandbox",
                "match_id": match_id,
                "scenario": scenario.to_json(),
                "runtime_template": runtime_template,
                "action_policy": action_policy,
                "resource_budget": resource_budget,
                "lease_duration_seconds": resolved_lease,
            }
        )
        sandbox_id = _new_id("sandbox")
        allocation = self.provider.provision(sandbox_id=sandbox_id, match_id=match_id)
        return self.repository.provision_sandbox(
            sandbox_id=sandbox_id,
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            match_id=match_id,
            scenario=scenario,
            runtime_template=runtime_template,
            action_policy=action_policy,
            resource_budget=resource_budget,
            lease_duration_seconds=resolved_lease,
            provider_name=self.provider.name,
            allocation=allocation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            retention_hours=self.settings.idempotency_retention_hours,
        )


def _request_hash(payload: dict[str, Any]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
