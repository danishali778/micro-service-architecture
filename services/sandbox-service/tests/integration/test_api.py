from conftest import auth_headers, idempotency_headers, provision_payload
from fastapi.testclient import TestClient


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_provision_read_and_terminate_sandbox(client: TestClient) -> None:
    create_response = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={**auth_headers(), **idempotency_headers("provision-1")},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["state"] == "ready"
    assert created["status_reason"] == "local_provider_ready"
    assert created["provider"] == "local_fake"
    assert created["allocation"]["allocation_id"].startswith("local_sandbox_")
    assert created["ready_at"] is not None
    assert created["terminated_at"] is None

    get_response = client.get(
        f"/internal/v1/sandboxes/{created['id']}",
        headers=auth_headers(scopes="sandboxes:read"),
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]

    terminate_response = client.post(
        f"/internal/v1/sandboxes/{created['id']}/terminate",
        json={"reason": "match_cancelled"},
        headers={**auth_headers(scopes="sandboxes:terminate"), **idempotency_headers("term-1")},
    )
    assert terminate_response.status_code == 200
    terminated = terminate_response.json()
    assert terminated["state"] == "terminated"
    assert terminated["cleanup"] == {"status": "completed", "details": []}
    assert terminated["terminated_at"] is not None


def test_provision_is_idempotent(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("same-provision")}
    first = client.post("/internal/v1/sandboxes", json=provision_payload(), headers=headers)
    second = client.post("/internal/v1/sandboxes", json=provision_payload(), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_idempotency_conflict_is_rejected(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("conflict-key")}
    first = client.post(
        "/internal/v1/sandboxes", json=provision_payload("match_1"), headers=headers
    )
    second = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload("match_2"),
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_terminate_is_idempotent(client: TestClient) -> None:
    created = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={**auth_headers(), **idempotency_headers("create-term-replay")},
    ).json()
    headers = {**auth_headers(scopes="sandboxes:terminate"), **idempotency_headers("same-term")}

    first = client.post(
        f"/internal/v1/sandboxes/{created['id']}/terminate",
        json={"reason": "match_cancelled"},
        headers=headers,
    )
    second = client.post(
        f"/internal/v1/sandboxes/{created['id']}/terminate",
        json={"reason": "match_cancelled"},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["state"] == "terminated"


def test_cross_tenant_sandbox_read_is_hidden(client: TestClient) -> None:
    created = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={**auth_headers(tenant_id="tenant-1"), **idempotency_headers("tenant-create")},
    ).json()

    response = client.get(
        f"/internal/v1/sandboxes/{created['id']}",
        headers=auth_headers(tenant_id="tenant-2", scopes="sandboxes:read"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sandbox_not_found"


def test_invalid_lease_returns_stable_validation_error(client: TestClient) -> None:
    payload = provision_payload()
    payload["lease_duration_seconds"] = 999_999

    response = client.post(
        "/internal/v1/sandboxes",
        json=payload,
        headers={**auth_headers(), **idempotency_headers("bad-lease")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["correlation_id"]


def test_replaces_invalid_correlation_header(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={
            **auth_headers(correlation_id="not safe"),
            **idempotency_headers("bad-correlation"),
        },
    )

    assert response.status_code == 201
    assert response.headers["X-Correlation-ID"] != "not safe"
