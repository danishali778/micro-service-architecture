from dataclasses import dataclass

from app.application.queries.build_scenario_snapshot import BuildScenarioSnapshot
from app.application.queries.list_scenarios import ListScenarios
from app.infrastructure.database.health import ReadinessChecker
from app.security.internal_auth import InternalAuthValidator


@dataclass(frozen=True, slots=True)
class Services:
    list_scenarios: ListScenarios
    build_scenario_snapshot: BuildScenarioSnapshot
    readiness_checker: ReadinessChecker
    internal_auth_validator: InternalAuthValidator
