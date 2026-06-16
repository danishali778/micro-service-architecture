from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_services, require_scenarios_read
from app.api.schemas import ErrorResponse, ScenarioPageResponse, ScenarioResponse
from app.core.container import Services
from app.security.internal_auth import TrustedInternalContext

router = APIRouter(tags=["scenarios"])


@router.get(
    "/scenarios",
    response_model=ScenarioPageResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def list_scenarios(
    context: Annotated[TrustedInternalContext, Depends(require_scenarios_read)],
    services: Annotated[Services, Depends(get_services)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> ScenarioPageResponse:
    page = services.list_scenarios.execute(
        tenant_id=context.tenant_id,
        limit=limit,
        cursor=cursor,
    )
    return ScenarioPageResponse(
        items=[ScenarioResponse.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
    )
