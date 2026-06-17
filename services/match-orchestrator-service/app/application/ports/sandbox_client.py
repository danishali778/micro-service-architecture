from typing import Protocol

from app.domain.entities.match import SandboxProvision, ScenarioSnapshot
from app.security.internal_auth import TrustedInternalContext


class SandboxClient(Protocol):
    async def provision_sandbox(
        self,
        *,
        match_id: str,
        scenario: ScenarioSnapshot,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxProvision: ...

    async def terminate_sandbox(
        self,
        *,
        sandbox_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxProvision: ...
