from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_services, require_internal_context
from app.api.schemas import (
    AuthorizationDecisionRequest,
    AuthorizationDecisionResponse,
    ErrorResponse,
)
from app.core.container import Services
from app.core.exceptions import ForbiddenError
from app.domain.entities.identity import ResourceRef
from app.security.internal_auth import TrustedInternalContext

router = APIRouter(tags=["authorization"])


@router.post(
    "/authorization/decisions",
    response_model=AuthorizationDecisionResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def decide(
    body: AuthorizationDecisionRequest,
    context: Annotated[TrustedInternalContext, Depends(require_internal_context)],
    services: Annotated[Services, Depends(get_services)],
) -> AuthorizationDecisionResponse:
    if body.workload_id != context.workload_id:
        raise ForbiddenError()
    decision = services.evaluate_authorization.execute(
        subject_id=body.subject_id,
        tenant_id=body.tenant_id,
        workload_id=context.workload_id,
        action=body.action,
        resource=ResourceRef(type=body.resource.type, id=body.resource.id),
        correlation_id=context.correlation_id,
    )
    return AuthorizationDecisionResponse(
        decision=decision.decision,
        reason=decision.reason,
        policy_version=decision.policy_version,
        audit_id=decision.audit_id,
    )
