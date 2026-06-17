from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.dependencies import (
    get_services,
    require_sandboxes_provision,
    require_sandboxes_read,
    require_sandboxes_terminate,
)
from app.api.schemas import (
    CleanupResponse,
    ErrorResponse,
    ProvisionSandboxRequest,
    SandboxResponse,
    SandboxScenarioResponse,
    TerminateSandboxRequest,
)
from app.core.container import Services
from app.domain.entities.sandbox import SandboxRecord, SandboxScenario
from app.security.internal_auth import TrustedInternalContext

router = APIRouter(tags=["sandboxes"])


@router.post(
    "/sandboxes",
    response_model=SandboxResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
def provision_sandbox(
    body: ProvisionSandboxRequest,
    response: Response,
    context: Annotated[TrustedInternalContext, Depends(require_sandboxes_provision)],
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SandboxResponse:
    result = services.provision_sandbox.execute(
        match_id=body.match_id,
        scenario=SandboxScenario(
            snapshot_id=body.scenario.snapshot_id,
            scenario_id=body.scenario.scenario_id,
            version=body.scenario.version,
            title=body.scenario.title,
        ),
        runtime_template=body.runtime_template,
        action_policy=body.action_policy,
        resource_budget=body.resource_budget,
        lease_duration_seconds=body.lease_duration_seconds,
        idempotency_key=idempotency_key,
        context=context,
    )
    response.status_code = result.status_code
    return _sandbox_response(result.sandbox)


@router.get(
    "/sandboxes/{sandbox_id}",
    response_model=SandboxResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_sandbox(
    sandbox_id: str,
    context: Annotated[TrustedInternalContext, Depends(require_sandboxes_read)],
    services: Annotated[Services, Depends(get_services)],
) -> SandboxResponse:
    return _sandbox_response(services.get_sandbox.execute(sandbox_id=sandbox_id, context=context))


@router.post(
    "/sandboxes/{sandbox_id}/terminate",
    response_model=SandboxResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
def terminate_sandbox(
    sandbox_id: str,
    body: TerminateSandboxRequest,
    response: Response,
    context: Annotated[TrustedInternalContext, Depends(require_sandboxes_terminate)],
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SandboxResponse:
    result = services.terminate_sandbox.execute(
        sandbox_id=sandbox_id,
        reason=body.reason,
        idempotency_key=idempotency_key,
        context=context,
    )
    response.status_code = result.status_code
    return _sandbox_response(result.sandbox)


def _sandbox_response(sandbox: SandboxRecord) -> SandboxResponse:
    return SandboxResponse(
        id=sandbox.id,
        tenant_id=sandbox.tenant_id,
        subject_id=sandbox.subject_id,
        match_id=sandbox.match_id,
        scenario=SandboxScenarioResponse(
            snapshot_id=sandbox.scenario.snapshot_id,
            scenario_id=sandbox.scenario.scenario_id,
            version=sandbox.scenario.version,
            title=sandbox.scenario.title,
        ),
        state=sandbox.state,
        status_reason=sandbox.status_reason,
        provider=sandbox.provider,
        allocation=sandbox.allocation,
        lease_expires_at=sandbox.lease_expires_at,
        created_at=sandbox.created_at,
        updated_at=sandbox.updated_at,
        ready_at=sandbox.ready_at,
        terminated_at=sandbox.terminated_at,
        failed_at=sandbox.failed_at,
        cleanup=CleanupResponse(
            status=sandbox.cleanup.status,
            details=sandbox.cleanup.details,
        )
        if sandbox.cleanup is not None
        else None,
    )
