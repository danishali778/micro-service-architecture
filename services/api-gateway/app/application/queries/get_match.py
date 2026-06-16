from dataclasses import dataclass

from app.application.ports.match_client import MatchClient
from app.domain.matches import Match
from app.domain.value_objects.tenant_context import TrustedRequestContext


@dataclass(frozen=True, slots=True)
class GetMatch:
    client: MatchClient

    async def execute(
        self,
        *,
        match_id: str,
        context: TrustedRequestContext,
    ) -> Match:
        return await self.client.get_match(match_id=match_id, context=context)
