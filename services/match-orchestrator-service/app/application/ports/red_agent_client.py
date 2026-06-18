from typing import Protocol

from app.domain.entities.match import RedRunResult, SandboxProvision, ScenarioSnapshot
from app.security.internal_auth import TrustedInternalContext


class RedAgentClient(Protocol):
    async def start_red_run(
        self,
        *,
        match_id: str,
        scenario: ScenarioSnapshot,
        sandbox: SandboxProvision,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> RedRunResult: ...
