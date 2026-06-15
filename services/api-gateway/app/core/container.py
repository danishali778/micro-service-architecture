from dataclasses import dataclass

from app.application.queries.list_scenarios import ListScenarios
from app.security.token_validator import TokenValidator


@dataclass(frozen=True, slots=True)
class Services:
    token_validator: TokenValidator
    list_scenarios: ListScenarios
