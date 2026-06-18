from conftest import auth_headers, idempotency_headers, red_run_payload
from fastapi.testclient import TestClient


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_start_and_get_red_run(client: TestClient) -> None:
    create_response = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers={**auth_headers(), **idempotency_headers("start-1")},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["state"] == "proposal_ready"
    assert created["status_reason"] == "fake_agent_proposal_ready"
    assert created["agent"] == {"adapter": "local_fake", "profile_ref": "red-agent-local-fake@1"}
    assert created["proposal"]["proposal_type"] == "http_request"
    assert created["proposal"]["action"]["method"] == "POST"

    get_response = client.get(
        f"/internal/v1/red-runs/{created['id']}",
        headers=auth_headers(scopes="red:runs:read"),
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_start_red_run_is_idempotent(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("same-red")}
    first = client.post("/internal/v1/red-runs", json=red_run_payload(), headers=headers)
    second = client.post("/internal/v1/red-runs", json=red_run_payload(), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_idempotency_conflict_is_rejected(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("conflict-red")}
    first = client.post("/internal/v1/red-runs", json=red_run_payload("match_1"), headers=headers)
    second = client.post("/internal/v1/red-runs", json=red_run_payload("match_2"), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_cross_tenant_red_run_read_is_hidden(client: TestClient) -> None:
    created = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers={**auth_headers(tenant_id="tenant-1"), **idempotency_headers("tenant-red")},
    ).json()

    response = client.get(
        f"/internal/v1/red-runs/{created['id']}",
        headers=auth_headers(tenant_id="tenant-2", scopes="red:runs:read"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "red_run_not_found"


def test_replaces_invalid_correlation_header(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers={
            **auth_headers(correlation_id="not safe"),
            **idempotency_headers("bad-correlation"),
        },
    )

    assert response.status_code == 201
    assert response.headers["X-Correlation-ID"] != "not safe"
