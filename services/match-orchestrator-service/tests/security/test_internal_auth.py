from conftest import auth_headers, idempotency_headers
from fastapi.testclient import TestClient


def test_create_match_requires_internal_auth(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
    )

    assert response.status_code == 401


def test_create_match_requires_gateway_workload(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers={
            **auth_headers(workload_id="admin-tooling"),
            **idempotency_headers(),
        },
    )

    assert response.status_code == 403


def test_create_match_requires_scope(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers={**auth_headers(scopes="matches:read"), **idempotency_headers()},
    )

    assert response.status_code == 403


def test_create_match_requires_idempotency_key(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_internal_auth_requires_tenant_and_subject(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers()}
    del headers["X-Internal-Tenant-ID"]

    response = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=headers,
    )

    assert response.status_code == 401
