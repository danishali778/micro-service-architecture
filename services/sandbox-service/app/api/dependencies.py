from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.container import Services
from app.security.internal_auth import (
    TrustedInternalContext,
    require_orchestrator_scope,
)


def get_services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def require_sandboxes_provision(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_orchestrator_scope(context, "sandboxes:provision")
    return context


def require_sandboxes_read(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_orchestrator_scope(context, "sandboxes:read")
    return context


def require_sandboxes_terminate(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_orchestrator_scope(context, "sandboxes:terminate")
    return context
