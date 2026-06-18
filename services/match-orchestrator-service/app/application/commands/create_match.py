from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.application.ports.match_repository import MatchRepository
from app.application.ports.red_agent_client import RedAgentClient
from app.application.ports.sandbox_client import SandboxClient
from app.application.ports.scenario_client import ScenarioClient
from app.core.config import Settings
from app.domain.entities.match import MatchOperationResult
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class CreateMatch:
    repository: MatchRepository
    scenario_client: ScenarioClient
    sandbox_client: SandboxClient
    red_agent_client: RedAgentClient
    settings: Settings

    async def execute(
        self,
        *,
        scenario_id: str,
        scenario_version: str | None,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> MatchOperationResult:
        request_hash = _request_hash(
            {
                "operation": "create_match",
                "scenario_id": scenario_id,
                "scenario_version": scenario_version,
            }
        )
        snapshot = await self.scenario_client.build_snapshot(
            scenario_id=scenario_id,
            version=scenario_version,
            context=context,
        )
        match_id = _match_id(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            idempotency_key=idempotency_key,
        )
        sandbox = await self.sandbox_client.provision_sandbox(
            match_id=match_id,
            scenario=snapshot,
            idempotency_key=idempotency_key,
            context=context,
        )
        match_result = self.repository.ensure_sandbox_ready_match(
            match_id=match_id,
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            scenario=snapshot,
            sandbox=sandbox,
        )
        if match_result.match.state == "red_proposal_ready":
            return match_result
        red_run = await self.red_agent_client.start_red_run(
            match_id=match_id,
            scenario=snapshot,
            sandbox=sandbox,
            idempotency_key=idempotency_key,
            context=context,
        )
        return self.repository.mark_red_proposal_ready(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            match_id=match_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            red_run=red_run,
            retention_hours=self.settings.idempotency_retention_hours,
        )


def _request_hash(payload: dict[str, object]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _match_id(*, tenant_id: str, subject_id: str, idempotency_key: str) -> str:
    digest = sha256(f"{tenant_id}:{subject_id}:{idempotency_key}".encode()).hexdigest()
    return f"match_{digest[:32]}"
