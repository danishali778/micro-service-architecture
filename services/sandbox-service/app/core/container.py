from dataclasses import dataclass

from app.application.commands.provision_sandbox import ProvisionSandbox
from app.application.commands.terminate_sandbox import TerminateSandbox
from app.application.queries.get_sandbox import GetSandbox
from app.infrastructure.database.health import ReadinessChecker
from app.security.internal_auth import InternalAuthValidator


@dataclass(frozen=True, slots=True)
class Services:
    provision_sandbox: ProvisionSandbox
    get_sandbox: GetSandbox
    terminate_sandbox: TerminateSandbox
    readiness_checker: ReadinessChecker
    internal_auth_validator: InternalAuthValidator
