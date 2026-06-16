from conftest import auth_headers
from fastapi.testclient import TestClient


def test_scenario_listing_requires_internal_auth(client: TestClient) -> None:
    response = client.get("/internal/v1/scenarios")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_scenario_listing_requires_gateway_workload(client: TestClient) -> None:
    response = client.get(
        "/internal/v1/scenarios",
        headers=auth_headers(workload_id="match-orchestrator-service"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_scenario_listing_requires_scope(client: TestClient) -> None:
    response = client.get(
        "/internal/v1/scenarios",
        headers=auth_headers(scopes="matches:read"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_scenario_listing_requires_tenant_and_subject(client: TestClient) -> None:
    headers = auth_headers()
    del headers["X-Internal-Tenant-ID"]

    response = client.get("/internal/v1/scenarios", headers=headers)

    assert response.status_code == 401


def test_snapshot_requires_orchestrator_workload(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/scenario-snapshots",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=auth_headers(scopes="matches:create"),
    )

    assert response.status_code == 403


def test_snapshot_requires_match_create_scope(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/scenario-snapshots",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=auth_headers(workload_id="match-orchestrator-service", scopes="scenarios:read"),
    )

    assert response.status_code == 403
