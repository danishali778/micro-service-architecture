from dataclasses import dataclass

from app.application.ports.scenario_client import ScenarioClient
from app.domain.scenarios import ScenarioPage
from app.domain.value_objects.tenant_context import TrustedRequestContext


@dataclass(frozen=True, slots=True)
class ListScenarios:
    scenario_client: ScenarioClient

    async def execute(
        self,
        *,
        limit: int,
        cursor: str | None,
        context: TrustedRequestContext,
    ) -> ScenarioPage:
        return await self.scenario_client.list_scenarios(
            limit=limit,
            cursor=cursor,
            context=context,
        )
