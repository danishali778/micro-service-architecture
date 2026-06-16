from dataclasses import dataclass

from app.application.ports.match_client import MatchClient
from app.domain.matches import Match
from app.domain.value_objects.tenant_context import TrustedRequestContext


@dataclass(frozen=True, slots=True)
class CancelMatch:
    client: MatchClient

    async def execute(
        self,
        *,
        match_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match:
        return await self.client.cancel_match(
            match_id=match_id,
            reason=reason,
            idempotency_key=idempotency_key,
            context=context,
        )
