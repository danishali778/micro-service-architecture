from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.api.dependencies import get_services
from app.api.schemas import (
    AgentResponse,
    AttackProposalResponse,
    ErrorResponse,
    RedRunResponse,
    RedScenarioResponse,
    StartRedRunRequest,
)
from app.core.container import Services
from app.core.exceptions import AuthenticationError
from app.domain.entities.red_run import RedRunRecord, RedRunRequest, RedScenario

router = APIRouter(tags=["red-runs"])


@router.post(
    "/red-runs",
    response_model=RedRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def start_red_run(
    payload: StartRedRunRequest,
    request: Request,
    response: Response,
    services: Annotated[Services, Depends(get_services)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RedRunResponse:
    if idempotency_key is None or idempotency_key.strip() == "":
        raise AuthenticationError("Idempotency-Key is required.", code="missing_idempotency_key")
    context = services.internal_auth_validator.validate(
        request,
        required_workload="match-orchestrator-service",
    )
    context.require_scope("red:runs:start")
    command = RedRunRequest(
        match_id=payload.match_id,
        sandbox_id=payload.sandbox_id,
        scenario=RedScenario(
            snapshot_id=payload.scenario.snapshot_id,
            scenario_id=payload.scenario.scenario_id,
            version=payload.scenario.version,
            title=payload.scenario.title,
        ),
        target_profile=payload.target_profile,
        action_policy=payload.action_policy,
        resource_budget=payload.resource_budget,
        agent_profile_ref=payload.agent_profile_ref
        or services.start_red_run.settings.default_agent_profile_ref,
    )
    result = await services.start_red_run.execute(
        request=command,
        idempotency_key=idempotency_key,
        context=context,
    )
    response.status_code = result.status_code
    return _red_run_response(result.red_run)


@router.get(
    "/red-runs/{red_run_id}",
    response_model=RedRunResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_red_run(
    red_run_id: str,
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> RedRunResponse:
    context = services.internal_auth_validator.validate(
        request,
        required_workload="match-orchestrator-service",
    )
    context.require_scope("red:runs:read")
    return _red_run_response(services.get_red_run.execute(red_run_id=red_run_id, context=context))


def _red_run_response(red_run: RedRunRecord) -> RedRunResponse:
    return RedRunResponse(
        id=red_run.id,
        tenant_id=red_run.tenant_id,
        subject_id=red_run.subject_id,
        match_id=red_run.match_id,
        sandbox_id=red_run.sandbox_id,
        scenario=RedScenarioResponse(
            snapshot_id=red_run.scenario.snapshot_id,
            scenario_id=red_run.scenario.scenario_id,
            version=red_run.scenario.version,
            title=red_run.scenario.title,
        ),
        state=red_run.state,
        status_reason=red_run.status_reason,
        agent=AgentResponse(
            adapter=red_run.agent.adapter,
            profile_ref=red_run.agent.profile_ref,
        ),
        proposal=AttackProposalResponse(
            proposal_id=red_run.proposal.proposal_id,
            proposal_type=red_run.proposal.proposal_type,
            title=red_run.proposal.title,
            summary=red_run.proposal.summary,
            rationale=red_run.proposal.rationale,
            action=red_run.proposal.action,
            expected_signal=red_run.proposal.expected_signal,
            risk_level=red_run.proposal.risk_level,
            confidence=red_run.proposal.confidence,
        )
        if red_run.proposal is not None
        else None,
        created_at=red_run.created_at,
        updated_at=red_run.updated_at,
        completed_at=red_run.completed_at,
        failed_at=red_run.failed_at,
    )
