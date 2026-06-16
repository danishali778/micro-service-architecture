from app.domain.entities.identity import ResourceRef
from app.infrastructure.database.connection import create_session_factory
from app.infrastructure.database.models import Base
from app.infrastructure.database.repositories import SqlAlchemyIdentityRepository
from sqlalchemy import create_engine


def make_repository() -> SqlAlchemyIdentityRepository:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SqlAlchemyIdentityRepository(create_session_factory(engine))


def test_repository_resolves_scopes_and_session_context() -> None:
    repository = make_repository()
    repository.create_role(
        role_code="security_learner",
        display_name="Security Learner",
        scopes=frozenset({"scenarios:read", "matches:read"}),
    )
    repository.create_tenant(
        tenant_id="tenant-1",
        slug="tenant-1",
        display_name="Tenant 1",
    )
    repository.create_user(
        user_id="user-1",
        supabase_user_id="supabase-user-1",
        email="learner@example.com",
        display_name="Learner",
    )
    repository.assign_membership(
        membership_id="membership-1",
        tenant_id="tenant-1",
        user_id="user-1",
    )
    repository.assign_role(
        role_assignment_id="role-assignment-1",
        membership_id="membership-1",
        role_code="security_learner",
    )
    repository.record_session(
        supabase_user_id="supabase-user-1",
        session_id="session-1",
        tenant_id="tenant-1",
        user_id="user-1",
    )

    context = repository.session_context_for_session(
        supabase_user_id="supabase-user-1",
        session_id="session-1",
    )

    assert context is not None
    assert context.subject_id == "user-1"
    assert context.tenant_id == "tenant-1"
    assert context.scopes == frozenset({"scenarios:read", "matches:read"})


def test_repository_rejects_revoked_session() -> None:
    repository = make_repository()
    repository.create_role(
        role_code="security_learner",
        display_name="Security Learner",
        scopes=frozenset({"scenarios:read"}),
    )
    repository.create_tenant(tenant_id="tenant-1", slug="tenant-1", display_name="Tenant 1")
    repository.create_user(
        user_id="user-1",
        supabase_user_id="supabase-user-1",
        email="learner@example.com",
        display_name=None,
    )
    repository.assign_membership(
        membership_id="membership-1",
        tenant_id="tenant-1",
        user_id="user-1",
    )
    repository.assign_role(
        role_assignment_id="role-assignment-1",
        membership_id="membership-1",
        role_code="security_learner",
    )
    repository.record_session(
        supabase_user_id="supabase-user-1",
        session_id="session-1",
        tenant_id="tenant-1",
        user_id="user-1",
    )
    repository.revoke_session(supabase_user_id="supabase-user-1", session_id="session-1")

    assert (
        repository.session_context_for_session(
            supabase_user_id="supabase-user-1",
            session_id="session-1",
        )
        is None
    )


def test_repository_records_authorization_decision() -> None:
    repository = make_repository()
    repository.create_role(
        role_code="security_learner",
        display_name="Security Learner",
        scopes=frozenset({"scenarios:read"}),
    )
    repository.create_tenant(tenant_id="tenant-1", slug="tenant-1", display_name="Tenant 1")
    repository.create_user(
        user_id="user-1",
        supabase_user_id="supabase-user-1",
        email="learner@example.com",
        display_name=None,
    )
    repository.assign_membership(
        membership_id="membership-1",
        tenant_id="tenant-1",
        user_id="user-1",
    )
    repository.assign_role(
        role_assignment_id="role-assignment-1",
        membership_id="membership-1",
        role_code="security_learner",
    )

    allowed = repository.evaluate_authorization(
        subject_id="user-1",
        tenant_id="tenant-1",
        workload_id="scenario-service",
        action="scenario.read",
        resource=ResourceRef(type="scenario", id="scn_1"),
        required_scope="scenarios:read",
        correlation_id="correlation-1",
    )
    denied = repository.evaluate_authorization(
        subject_id="user-1",
        tenant_id="tenant-1",
        workload_id="scenario-service",
        action="scenario.publish",
        resource=ResourceRef(type="scenario", id="scn_1"),
        required_scope="admin:scenarios",
        correlation_id="correlation-1",
    )

    assert allowed.decision == "allow"
    assert denied.decision == "deny"
