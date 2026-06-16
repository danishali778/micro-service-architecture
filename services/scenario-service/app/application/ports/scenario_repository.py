from typing import Protocol

from app.domain.entities.scenario import ScenarioPage, ScenarioSnapshot


class ScenarioRepository(Protocol):
    def list_visible_published(
        self,
        *,
        tenant_id: str,
        limit: int,
        offset: int,
    ) -> ScenarioPage: ...

    def build_snapshot(
        self,
        *,
        tenant_id: str,
        scenario_id: str,
        version: str | None,
    ) -> ScenarioSnapshot | None: ...
