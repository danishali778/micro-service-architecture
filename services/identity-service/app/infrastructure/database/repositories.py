from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError
from app.domain.entities.identity import AuthorizationDecision, ResourceRef, SessionContext
from app.domain.policies.authorization_policy import POLICY_VERSION
from app.infrastructure.database.connection import SessionFactory
from app.infrastructure.database.models import (
    AuthorizationAuditModel,
    AuthSessionModel,
    MembershipModel,
    RoleAssignmentModel,
    RoleModel,
    RoleScopeModel,
    ScopeModel,
    TenantModel,
    UserModel,
)


class SqlAlchemyIdentityRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def session_context_for_login(
        self,
        *,
        supabase_user_id: str,
        tenant_id: str,
    ) -> SessionContext | None:
        return self._context_for_user_tenant(
            supabase_user_id=supabase_user_id,
            tenant_id=tenant_id,
        )

    def session_context_for_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
    ) -> SessionContext | None:
        with self._session_factory() as session:
            auth_session = session.scalar(
                select(AuthSessionModel).where(
                    AuthSessionModel.supabase_user_id == supabase_user_id,
                    AuthSessionModel.session_id == session_id,
                    AuthSessionModel.status == "active",
                )
            )
            if auth_session is None:
                return None
            tenant_id = auth_session.tenant_id

        return self._context_for_user_tenant(
            supabase_user_id=supabase_user_id,
            tenant_id=tenant_id,
        )

    def session_context_for_subject_tenant(
        self,
        *,
        subject_id: str,
        tenant_id: str,
    ) -> SessionContext | None:
        with self._session_factory() as session:
            user = session.scalar(
                select(UserModel).where(
                    UserModel.user_id == subject_id,
                    UserModel.status == "active",
                )
            )
            if user is None:
                return None
            supabase_user_id = user.supabase_user_id

        return self._context_for_user_tenant(
            supabase_user_id=supabase_user_id,
            tenant_id=tenant_id,
        )

    def record_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> None:
        with self._session_factory() as session:
            auth_session = session.scalar(
                select(AuthSessionModel).where(
                    AuthSessionModel.supabase_user_id == supabase_user_id,
                    AuthSessionModel.session_id == session_id,
                )
            )
            if auth_session is None:
                session.add(
                    AuthSessionModel(
                        auth_session_id=_new_id("authsess"),
                        supabase_user_id=supabase_user_id,
                        session_id=session_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        status="active",
                    )
                )
            else:
                auth_session.status = "active"
                auth_session.tenant_id = tenant_id
                auth_session.user_id = user_id
            session.commit()

    def revoke_session(
        self,
        *,
        supabase_user_id: str,
        session_id: str,
    ) -> None:
        with self._session_factory() as session:
            auth_session = session.scalar(
                select(AuthSessionModel).where(
                    AuthSessionModel.supabase_user_id == supabase_user_id,
                    AuthSessionModel.session_id == session_id,
                )
            )
            if auth_session is not None:
                auth_session.status = "revoked"
                session.commit()

    def create_tenant(
        self,
        *,
        tenant_id: str,
        slug: str,
        display_name: str,
    ) -> None:
        with self._session_factory() as session:
            session.add(
                TenantModel(
                    tenant_id=tenant_id,
                    slug=slug,
                    display_name=display_name,
                    status="active",
                )
            )
            _commit_or_conflict(session)

    def create_user(
        self,
        *,
        user_id: str,
        supabase_user_id: str,
        email: str,
        display_name: str | None,
    ) -> None:
        with self._session_factory() as session:
            session.add(
                UserModel(
                    user_id=user_id,
                    supabase_user_id=supabase_user_id,
                    email=email.lower(),
                    display_name=display_name,
                    status="active",
                )
            )
            _commit_or_conflict(session)

    def assign_membership(
        self,
        *,
        membership_id: str,
        tenant_id: str,
        user_id: str,
    ) -> None:
        with self._session_factory() as session:
            session.add(
                MembershipModel(
                    membership_id=membership_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    status="active",
                )
            )
            _commit_or_conflict(session)

    def create_role(self, *, role_code: str, display_name: str, scopes: frozenset[str]) -> None:
        with self._session_factory() as session:
            role = session.get(RoleModel, role_code)
            if role is None:
                session.add(
                    RoleModel(
                        role_code=role_code,
                        display_name=display_name,
                        description=None,
                    )
                )
            for scope in sorted(scopes):
                if session.get(ScopeModel, scope) is None:
                    session.add(ScopeModel(scope=scope, description=None))
                existing = session.scalar(
                    select(RoleScopeModel).where(
                        RoleScopeModel.role_code == role_code,
                        RoleScopeModel.scope == scope,
                    )
                )
                if existing is None:
                    session.add(
                        RoleScopeModel(
                            role_scope_id=_new_id("rolescope"),
                            role_code=role_code,
                            scope=scope,
                        )
                    )
            session.commit()

    def assign_role(
        self,
        *,
        role_assignment_id: str,
        membership_id: str,
        role_code: str,
    ) -> None:
        with self._session_factory() as session:
            session.add(
                RoleAssignmentModel(
                    role_assignment_id=role_assignment_id,
                    membership_id=membership_id,
                    role_code=role_code,
                    status="active",
                )
            )
            _commit_or_conflict(session)

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
    ) -> AuthorizationDecision:
        context = self.session_context_for_subject_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        decision = "allow" if context is not None and required_scope in context.scopes else "deny"
        reason = "scope_present" if decision == "allow" else "missing_permission"
        audit_id = _new_id("aud")

        with self._session_factory() as session:
            session.add(
                AuthorizationAuditModel(
                    audit_id=audit_id,
                    subject_id=subject_id,
                    tenant_id=tenant_id,
                    workload_id=workload_id,
                    action=action,
                    resource_type=resource.type,
                    resource_id=resource.id,
                    decision=decision,
                    reason=reason,
                    policy_version=POLICY_VERSION,
                    correlation_id=correlation_id,
                )
            )
            session.commit()

        return AuthorizationDecision(
            decision=decision,
            reason=reason,
            policy_version=POLICY_VERSION,
            audit_id=audit_id,
        )

    def _context_for_user_tenant(
        self,
        *,
        supabase_user_id: str,
        tenant_id: str,
    ) -> SessionContext | None:
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    UserModel.user_id,
                    UserModel.supabase_user_id,
                    MembershipModel.tenant_id,
                    RoleScopeModel.scope,
                )
                .join(MembershipModel, MembershipModel.user_id == UserModel.user_id)
                .join(TenantModel, TenantModel.tenant_id == MembershipModel.tenant_id)
                .join(
                    RoleAssignmentModel,
                    RoleAssignmentModel.membership_id == MembershipModel.membership_id,
                )
                .join(RoleScopeModel, RoleScopeModel.role_code == RoleAssignmentModel.role_code)
                .where(
                    UserModel.supabase_user_id == supabase_user_id,
                    UserModel.status == "active",
                    TenantModel.tenant_id == tenant_id,
                    TenantModel.status == "active",
                    MembershipModel.status == "active",
                    RoleAssignmentModel.status == "active",
                )
            ).all()

        if not rows:
            return None

        first = rows[0]
        return SessionContext(
            subject_id=str(first.user_id),
            supabase_user_id=str(first.supabase_user_id),
            tenant_id=str(first.tenant_id),
            scopes=frozenset(str(row.scope) for row in rows if row.scope),
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _commit_or_conflict(session: object) -> None:
    try:
        session.commit()  # type: ignore[attr-defined]
    except IntegrityError as error:
        session.rollback()  # type: ignore[attr-defined]
        raise ConflictError() from error
