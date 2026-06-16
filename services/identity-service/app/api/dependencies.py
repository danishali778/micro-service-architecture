from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.container import Services
from app.security.internal_auth import (
    TrustedInternalContext,
    require_admin_tooling,
    require_gateway,
)


def get_services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def require_gateway_context(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_gateway(context)
    return context


def require_admin_context(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_admin_tooling(context)
    return context


def require_internal_context(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    return services.internal_auth_validator.authenticate(request)
