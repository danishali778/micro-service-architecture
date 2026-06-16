from dataclasses import dataclass

from app.application.commands.cancel_match import CancelMatch
from app.application.commands.create_match import CreateMatch
from app.application.ports.identity_client import IdentityClient
from app.application.queries.get_match import GetMatch
from app.application.queries.list_scenarios import ListScenarios
from app.security.token_validator import TokenValidator


@dataclass(frozen=True, slots=True)
class Services:
    token_validator: TokenValidator
    identity_client: IdentityClient
    list_scenarios: ListScenarios
    create_match: CreateMatch
    get_match: GetMatch
    cancel_match: CancelMatch
