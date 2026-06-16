from dataclasses import dataclass

from app.application.commands.cancel_match import CancelMatch
from app.application.commands.create_match import CreateMatch
from app.application.queries.get_match import GetMatch
from app.infrastructure.database.health import ReadinessChecker
from app.security.internal_auth import InternalAuthValidator


@dataclass(frozen=True, slots=True)
class Services:
    create_match: CreateMatch
    get_match: GetMatch
    cancel_match: CancelMatch
    readiness_checker: ReadinessChecker
    internal_auth_validator: InternalAuthValidator
