from dataclasses import dataclass

from app.application.ports.scenario_repository import ScenarioRepository
from app.domain.entities.scenario import ScenarioPage
from app.domain.value_objects.pagination import decode_offset_cursor


@dataclass(frozen=True, slots=True)
class ListScenarios:
    repository: ScenarioRepository

    def execute(
        self,
        *,
        tenant_id: str,
        limit: int,
        cursor: str | None,
    ) -> ScenarioPage:
        offset = decode_offset_cursor(cursor)
        return self.repository.list_visible_published(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
