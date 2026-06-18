from conftest import auth_headers, idempotency_headers, red_run_payload
from fastapi.testclient import TestClient


def test_missing_internal_auth_returns_401(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers=idempotency_headers("missing-auth"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_internal_auth"


def test_wrong_workload_returns_403(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers={
            **auth_headers(workload_id="sandbox-service"),
            **idempotency_headers("wrong-workload"),
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "wrong_workload"


def test_missing_scope_returns_403(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers={
            **auth_headers(scopes="red:runs:read"),
            **idempotency_headers("missing-scope"),
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "missing_scope"


def test_policy_denial_returns_safe_409(client: TestClient) -> None:
    payload = red_run_payload()
    payload["action_policy"] = {"allowed_tools": ["shell"]}

    response = client.post(
        "/internal/v1/red-runs",
        json=payload,
        headers={**auth_headers(), **idempotency_headers("policy-denied")},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "proposal_policy_denied"
