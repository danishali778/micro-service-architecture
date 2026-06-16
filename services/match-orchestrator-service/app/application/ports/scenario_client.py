from typing import Protocol

from app.domain.entities.match import ScenarioSnapshot
from app.security.internal_auth import TrustedInternalContext


class ScenarioClient(Protocol):
    async def build_snapshot(
        self,
        *,
        scenario_id: str,
        version: str | None,
        context: TrustedInternalContext,
    ) -> ScenarioSnapshot: ...
