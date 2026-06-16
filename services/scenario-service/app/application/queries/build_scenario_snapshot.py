from dataclasses import dataclass

from app.application.ports.scenario_repository import ScenarioRepository
from app.core.exceptions import NotFoundError
from app.domain.entities.scenario import ScenarioSnapshot


@dataclass(frozen=True, slots=True)
class BuildScenarioSnapshot:
    repository: ScenarioRepository

    def execute(
        self,
        *,
        tenant_id: str,
        scenario_id: str,
        version: str | None,
    ) -> ScenarioSnapshot:
        snapshot = self.repository.build_snapshot(
            tenant_id=tenant_id,
            scenario_id=scenario_id,
            version=version,
        )
        if snapshot is None:
            raise NotFoundError(
                code="scenario_not_found",
                message="The requested scenario was not found.",
            )
        return snapshot
