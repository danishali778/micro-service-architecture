from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.container import Services
from app.security.internal_auth import (
    TrustedInternalContext,
    require_gateway_scope,
)


def get_services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def require_matches_create(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_gateway_scope(context, "matches:create")
    return context


def require_matches_read(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_gateway_scope(context, "matches:read")
    return context


def require_matches_cancel(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_gateway_scope(context, "matches:cancel")
    return context
