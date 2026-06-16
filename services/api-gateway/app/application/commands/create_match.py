from dataclasses import dataclass

from app.application.ports.match_client import MatchClient
from app.domain.matches import Match
from app.domain.value_objects.tenant_context import TrustedRequestContext


@dataclass(frozen=True, slots=True)
class CreateMatch:
    client: MatchClient

    async def execute(
        self,
        *,
        scenario_id: str,
        scenario_version: str | None,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match:
        return await self.client.create_match(
            scenario_id=scenario_id,
            scenario_version=scenario_version,
            idempotency_key=idempotency_key,
            context=context,
        )
