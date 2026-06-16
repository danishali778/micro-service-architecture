from typing import Protocol

from app.domain.entities.scenario import ScenarioPage


class ScenarioRepository(Protocol):
    def list_visible_published(
        self,
        *,
        tenant_id: str,
        limit: int,
        offset: int,
    ) -> ScenarioPage: ...
