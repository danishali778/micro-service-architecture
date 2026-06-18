from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.application.ports.agent import RedAgent
from app.application.ports.red_run_repository import RedRunRepository
from app.core.config import Settings
from app.domain.entities.red_run import RedRunOperationResult, RedRunRequest
from app.domain.policies.proposal_policy import (
    ensure_policy_allows_proposal,
    validate_proposal_shape,
)
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class StartRedRun:
    repository: RedRunRepository
    agent: RedAgent
    settings: Settings

    async def execute(
        self,
        *,
        request: RedRunRequest,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> RedRunOperationResult:
        request_hash = _request_hash(
            {
                "operation": "start_red_run",
                "match_id": request.match_id,
                "sandbox_id": request.sandbox_id,
                "scenario": request.scenario.to_json(),
                "target_profile": request.target_profile,
                "action_policy": request.action_policy,
                "resource_budget": request.resource_budget,
                "agent_profile_ref": request.agent_profile_ref,
            }
        )
        red_run_id = _red_run_id(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            idempotency_key=idempotency_key,
        )
        proposal = await self.agent.generate_proposal(request)
        validate_proposal_shape(proposal)
        ensure_policy_allows_proposal(proposal=proposal, action_policy=request.action_policy)
        return self.repository.start_red_run(
            red_run_id=red_run_id,
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            request=request,
            adapter_name=self.agent.adapter_name,
            proposal=proposal,
            retention_hours=self.settings.idempotency_retention_hours,
        )


def _request_hash(payload: dict[str, object]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _red_run_id(*, tenant_id: str, subject_id: str, idempotency_key: str) -> str:
    digest = sha256(f"{tenant_id}:{subject_id}:{idempotency_key}".encode()).hexdigest()
    return f"redrun_{digest[:32]}"
