from typing import Protocol

from app.domain.entities.identity import AuthorizationDecision, ResourceRef, SessionContext


class IdentityRepository(Protocol):
    def session_context_for_login(
        self,
        *,
        supabase_user_id: str,
        tenant_id: str,
    ) -> SessionContext | None: ...

    def session_context_for_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
    ) -> SessionContext | None: ...

    def session_context_for_subject_tenant(
        self,
        *,
        subject_id: str,
        tenant_id: str,
    ) -> SessionContext | None: ...

    def record_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> None: ...

    def revoke_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
    ) -> None: ...

    def create_tenant(
        self,
        *,
        tenant_id: str,
        slug: str,
        display_name: str,
    ) -> None: ...

    def create_user(
        self,
        *,
        user_id: str,
        supabase_user_id: str,
        email: str,
        display_name: str | None,
    ) -> None: ...

    def assign_membership(
        self,
        *,
        membership_id: str,
        tenant_id: str,
        user_id: str,
    ) -> None: ...

    def create_role(self, *, role_code: str, display_name: str, scopes: frozenset[str]) -> None: ...

    def assign_role(
        self,
        *,
        role_assignment_id: str,
        membership_id: str,
        role_code: str,
    ) -> None: ...

    def evaluate_authorization(
        self,
        *,
        subject_id: str,
        tenant_id: str,
        workload_id: str,
        action: str,
        resource: ResourceRef,
        required_scope: str,
        correlation_id: str,
    ) -> AuthorizationDecision: ...
