from typing import Protocol

from app.domain.matches import Match
from app.domain.value_objects.tenant_context import TrustedRequestContext


class MatchClient(Protocol):
    async def create_match(
        self,
        *,
        scenario_id: str,
        scenario_version: str | None,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match: ...

    async def get_match(
        self,
        *,
        match_id: str,
        context: TrustedRequestContext,
    ) -> Match: ...

    async def cancel_match(
        self,
        *,
        match_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedRequestContext,
    ) -> Match: ...
