from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.container import Services
from app.core.exceptions import UnauthorizedError
from app.domain.value_objects.tenant_context import Principal
from app.security.authorization import require_scope

_bearer = HTTPBearer(auto_error=False)


def get_services(request: Request) -> Services:
    return request.app.state.services  # type: ignore[no-any-return]


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    services: Annotated[Services, Depends(get_services)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    return await services.token_validator.validate(credentials.credentials)


async def require_scenarios_read(
    principal: Annotated[Principal, Depends(get_principal)],
) -> Principal:
    require_scope(principal, "scenarios:read")
    return principal
