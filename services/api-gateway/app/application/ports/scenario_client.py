from typing import Protocol

from app.domain.scenarios import ScenarioPage
from app.domain.value_objects.tenant_context import TrustedRequestContext


class ScenarioClient(Protocol):
    async def list_scenarios(
        self,
        *,
        limit: int,
        cursor: str | None,
        context: TrustedRequestContext,
    ) -> ScenarioPage: ...
