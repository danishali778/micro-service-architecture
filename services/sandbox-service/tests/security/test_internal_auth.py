from conftest import auth_headers, idempotency_headers, provision_payload
from fastapi.testclient import TestClient


def test_missing_internal_auth_returns_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers=idempotency_headers("missing-auth"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_wrong_workload_is_forbidden(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={
            **auth_headers(workload_id="api-gateway"),
            **idempotency_headers("wrong-workload"),
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_missing_scope_is_forbidden(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={
            **auth_headers(scopes="sandboxes:read"),
            **idempotency_headers("missing-scope"),
        },
    )

    assert response.status_code == 403


def test_missing_subject_is_unauthorized(client: TestClient) -> None:
    headers = {**auth_headers(), **idempotency_headers("missing-subject")}
    headers.pop("X-Internal-Subject-ID")

    response = client.post("/internal/v1/sandboxes", json=provision_payload(), headers=headers)

    assert response.status_code == 401
