from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.application.ports.match_repository import MatchRepository
from app.application.ports.scenario_client import ScenarioClient
from app.core.config import Settings
from app.domain.entities.match import MatchOperationResult
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class CreateMatch:
    repository: MatchRepository
    scenario_client: ScenarioClient
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
        return self.repository.create_match(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            scenario=snapshot,
            retention_hours=self.settings.idempotency_retention_hours,
        )


def _request_hash(payload: dict[str, object]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()
