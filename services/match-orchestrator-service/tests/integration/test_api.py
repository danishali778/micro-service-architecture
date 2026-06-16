from conftest import FakeScenarioClient, auth_headers, idempotency_headers
from fastapi.testclient import TestClient


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_create_read_and_cancel_match(
    client: TestClient,
    scenario_client: FakeScenarioClient,
) -> None:
    create_response = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login", "scenario_version": "1.0.0"},
        headers={**auth_headers(), **idempotency_headers("create-1")},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["state"] == "waiting_for_sandbox"
    assert created["phase"] == "setup"
    assert created["scenario"]["snapshot_id"] == "ssnap_sql_login_1_0_0"
    assert scenario_client.calls[0][0:2] == ("scn_sql_injection_login", "1.0.0")
    assert scenario_client.calls[0][2].tenant_id == "tenant-1"

    get_response = client.get(
        f"/internal/v1/matches/{created['id']}",
        headers=auth_headers(scopes="matches:read"),
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]

    cancel_response = client.post(
        f"/internal/v1/matches/{created['id']}/cancel",
        json={"reason": "user_requested"},
        headers={**auth_headers(scopes="matches:cancel"), **idempotency_headers("cancel-1")},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["state"] == "cancelled"
    assert cancel_response.json()["cancelled_at"] is not None


def test_create_match_is_idempotent(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("same-create")}
    first = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=headers,
    )
    second = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_idempotency_conflict_is_rejected(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("conflict-key")}
    first = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers=headers,
    )
    second = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "different"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_cross_tenant_match_read_is_hidden(client: TestClient) -> None:
    created = client.post(
        "/internal/v1/matches",
        json={"scenario_id": "scn_sql_injection_login"},
        headers={**auth_headers(tenant_id="tenant-1"), **idempotency_headers("create-tenant")},
    ).json()

    response = client.get(
        f"/internal/v1/matches/{created['id']}",
        headers=auth_headers(tenant_id="tenant-2", scopes="matches:read"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "match_not_found"
