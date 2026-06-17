from app.infrastructure.database.models import (
    OutboxRecordModel,
    SandboxAttemptModel,
    SandboxTransitionModel,
)
from conftest import auth_headers, idempotency_headers, provision_payload
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session


def test_provision_persists_attempts_transitions_and_outbox(
    client: TestClient,
    engine: Engine,
) -> None:
    response = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={**auth_headers(), **idempotency_headers("persist-provision")},
    )

    assert response.status_code == 201
    sandbox_id = response.json()["id"]
    with Session(engine) as session:
        attempts = session.scalars(
            select(SandboxAttemptModel).where(SandboxAttemptModel.sandbox_id == sandbox_id)
        ).all()
        transitions = session.scalars(
            select(SandboxTransitionModel).where(SandboxTransitionModel.sandbox_id == sandbox_id)
        ).all()
        outbox = session.scalars(
            select(OutboxRecordModel).where(OutboxRecordModel.aggregate_id == sandbox_id)
        ).all()

    assert [attempt.attempt_type for attempt in attempts] == ["provision"]
    assert [transition.to_state for transition in transitions] == [
        "requested",
        "provisioning",
        "ready",
    ]
    assert [record.message_type for record in outbox] == ["sandbox.ready"]


def test_terminate_persists_cleanup_transition_and_outbox(
    client: TestClient,
    engine: Engine,
) -> None:
    created = client.post(
        "/internal/v1/sandboxes",
        json=provision_payload(),
        headers={**auth_headers(), **idempotency_headers("persist-create")},
    ).json()

    response = client.post(
        f"/internal/v1/sandboxes/{created['id']}/terminate",
        json={"reason": "match_cancelled"},
        headers={
            **auth_headers(scopes="sandboxes:terminate"),
            **idempotency_headers("persist-term"),
        },
    )

    assert response.status_code == 200
    with Session(engine) as session:
        transitions = session.scalars(
            select(SandboxTransitionModel).where(SandboxTransitionModel.sandbox_id == created["id"])
        ).all()
        outbox = session.scalars(
            select(OutboxRecordModel).where(OutboxRecordModel.aggregate_id == created["id"])
        ).all()

    assert [transition.to_state for transition in transitions][-3:] == [
        "termination_requested",
        "terminating",
        "terminated",
    ]
    assert [record.message_type for record in outbox] == [
        "sandbox.ready",
        "sandbox.terminated",
    ]
