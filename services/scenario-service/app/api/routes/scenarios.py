from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_services, require_scenarios_read, require_snapshot_build
from app.api.schemas import (
    ErrorResponse,
    ScenarioPageResponse,
    ScenarioResponse,
    ScenarioSnapshotRequest,
    ScenarioSnapshotResponse,
)
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


@router.post(
    "/scenario-snapshots",
    response_model=ScenarioSnapshotResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def build_scenario_snapshot(
    body: ScenarioSnapshotRequest,
    context: Annotated[TrustedInternalContext, Depends(require_snapshot_build)],
    services: Annotated[Services, Depends(get_services)],
) -> ScenarioSnapshotResponse:
    snapshot = services.build_scenario_snapshot.execute(
        tenant_id=context.tenant_id,
        scenario_id=body.scenario_id,
        version=body.version,
    )
    return ScenarioSnapshotResponse.model_validate(snapshot)
