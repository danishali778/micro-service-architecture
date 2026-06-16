from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.container import Services
from app.security.internal_auth import (
    TrustedInternalContext,
    require_gateway_scenario_read,
    require_orchestrator_match_create,
)


def get_services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def require_scenarios_read(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_gateway_scenario_read(context)
    return context


def require_snapshot_build(
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TrustedInternalContext:
    context = services.internal_auth_validator.authenticate(request)
    require_orchestrator_match_create(context)
    return context
