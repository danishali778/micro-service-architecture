from dataclasses import dataclass

from app.application.commands.start_red_run import StartRedRun
from app.application.queries.get_red_run import GetRedRun
from app.infrastructure.database.health import ReadinessChecker
from app.security.internal_auth import InternalAuthValidator


@dataclass(frozen=True, slots=True)
class Services:
    start_red_run: StartRedRun
    get_red_run: GetRedRun
    readiness_checker: ReadinessChecker
    internal_auth_validator: InternalAuthValidator
