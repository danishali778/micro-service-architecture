from dataclasses import dataclass

from app.application.commands.admin import AssignMembership, AssignRole, CreateTenant, CreateUser
from app.application.commands.auth import AuthenticateUser, LogoutUserSession, RefreshUserSession
from app.application.queries.authorization import EvaluateAuthorization
from app.application.queries.session_context import ResolveSessionContext
from app.infrastructure.database.health import ReadinessChecker
from app.security.internal_auth import InternalAuthValidator


@dataclass(frozen=True, slots=True)
class Services:
    authenticate_user: AuthenticateUser
    refresh_user_session: RefreshUserSession
    logout_user_session: LogoutUserSession
    resolve_session_context: ResolveSessionContext
    evaluate_authorization: EvaluateAuthorization
    create_tenant: CreateTenant
    create_user: CreateUser
    assign_membership: AssignMembership
    assign_role: AssignRole
    readiness_checker: ReadinessChecker
    internal_auth_validator: InternalAuthValidator
