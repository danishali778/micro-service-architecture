from app.core.exceptions import InvalidCredentialsError
from conftest import FakeIdentityRepository, FakeSupabaseAuthProvider, auth_headers
from fastapi.testclient import TestClient


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


def test_login_requires_internal_gateway_auth(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/auth/login",
        json={
            "email": "learner@example.com",
            "password": "secret-password",
            "tenant_id": "tenant-1",
        },
    )

    assert response.status_code == 401


def test_login_with_supabase_and_records_platform_session(
    client: TestClient,
    auth_provider: FakeSupabaseAuthProvider,
    repository: FakeIdentityRepository,
) -> None:
    response = client.post(
        "/internal/v1/auth/login",
        json={
            "email": "learner@example.com",
            "password": "secret-password",
            "tenant_id": "tenant-1",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["tenant_id"] == "tenant-1"
    assert response.json()["scopes"] == ["matches:read", "scenarios:read"]
    assert auth_provider.login_calls == [("learner@example.com", "secret-password")]
    assert repository.recorded_sessions == [("supabase-user-1", "session-1", "tenant-1", "user-1")]


def test_login_failure_is_generic_and_does_not_leak_password(
    client: TestClient,
    auth_provider: FakeSupabaseAuthProvider,
) -> None:
    auth_provider.error = InvalidCredentialsError()

    response = client.post(
        "/internal/v1/auth/login",
        json={
            "email": "learner@example.com",
            "password": "secret-password",
            "tenant_id": "tenant-1",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert "secret-password" not in response.text


def test_login_denies_inactive_membership(
    client: TestClient,
    repository: FakeIdentityRepository,
) -> None:
    repository.active_context = False

    response = client.post(
        "/internal/v1/auth/login",
        json={
            "email": "learner@example.com",
            "password": "secret-password",
            "tenant_id": "tenant-1",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 403


def test_refresh_and_logout(
    client: TestClient,
    auth_provider: FakeSupabaseAuthProvider,
    repository: FakeIdentityRepository,
) -> None:
    refresh = client.post(
        "/internal/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
        headers=auth_headers(),
    )
    logout = client.post(
        "/internal/v1/auth/logout",
        json={"access_token": auth_provider.token_set.access_token},
        headers=auth_headers(),
    )

    assert refresh.status_code == 200
    assert logout.status_code == 204
    assert auth_provider.refresh_calls == ["refresh-token"]
    assert auth_provider.logout_calls == [auth_provider.token_set.access_token]
    assert repository.revoked_sessions == [("supabase-user-1", "session-1")]


def test_session_context_resolves_platform_subject(client: TestClient) -> None:
    response = client.get(
        "/internal/v1/auth/session-context?subject_id=supabase-user-1&session_id=session-1",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "subject_id": "user-1",
        "tenant_id": "tenant-1",
        "scopes": ["matches:read", "scenarios:read"],
    }


def test_authorization_decision_requires_matching_workload(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/authorization/decisions",
        json={
            "subject_id": "user-1",
            "tenant_id": "tenant-1",
            "action": "scenario.read",
            "resource": {"type": "scenario", "id": "scn_1"},
            "workload_id": "scenario-service",
        },
        headers=auth_headers(workload_id="api-gateway"),
    )

    assert response.status_code == 403


def test_authorization_decision_allows_when_scope_is_present(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/authorization/decisions",
        json={
            "subject_id": "user-1",
            "tenant_id": "tenant-1",
            "action": "scenario.read",
            "resource": {"type": "scenario", "id": "scn_1"},
            "workload_id": "scenario-service",
        },
        headers=auth_headers(workload_id="scenario-service"),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "allow"


def test_admin_basics_require_admin_tooling(
    client: TestClient,
    repository: FakeIdentityRepository,
) -> None:
    denied = client.post(
        "/internal/v1/tenants",
        json={"tenant_id": "tenant-1", "slug": "tenant-1", "display_name": "Tenant 1"},
        headers=auth_headers(workload_id="api-gateway"),
    )
    created = client.post(
        "/internal/v1/tenants",
        json={"tenant_id": "tenant-1", "slug": "tenant-1", "display_name": "Tenant 1"},
        headers=auth_headers(workload_id="admin-tooling"),
    )

    assert denied.status_code == 403
    assert created.status_code == 201
    assert repository.tenants == [("tenant-1", "tenant-1", "Tenant 1")]
