from app.application.ports.identity_repository import IdentityRepository
from app.domain.entities.identity import AuthorizationDecision, ResourceRef
from app.domain.policies.authorization_policy import required_scope_for_action


class EvaluateAuthorization:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        subject_id: str,
        tenant_id: str,
        workload_id: str,
        action: str,
        resource: ResourceRef,
        correlation_id: str,
    ) -> AuthorizationDecision:
        return self._repository.evaluate_authorization(
            subject_id=subject_id,
            tenant_id=tenant_id,
            workload_id=workload_id,
            action=action,
            resource=resource,
            required_scope=required_scope_for_action(action),
            correlation_id=correlation_id,
        )
