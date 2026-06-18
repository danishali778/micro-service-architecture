from app.infrastructure.database.models import (
    AttackProposalModel,
    OutboxRecordModel,
    RedRunAttemptModel,
    RedRunTransitionModel,
)
from conftest import auth_headers, idempotency_headers, red_run_payload
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session


def test_start_red_run_persists_attempt_proposal_transitions_and_outbox(
    client: TestClient,
    engine: Engine,
) -> None:
    response = client.post(
        "/internal/v1/red-runs",
        json=red_run_payload(),
        headers={**auth_headers(), **idempotency_headers("persist-red")},
    )

    assert response.status_code == 201
    red_run_id = response.json()["id"]
    with Session(engine) as session:
        attempts = session.scalars(
            select(RedRunAttemptModel).where(RedRunAttemptModel.red_run_id == red_run_id)
        ).all()
        proposals = session.scalars(
            select(AttackProposalModel).where(AttackProposalModel.red_run_id == red_run_id)
        ).all()
        transitions = session.scalars(
            select(RedRunTransitionModel).where(RedRunTransitionModel.red_run_id == red_run_id)
        ).all()
        outbox = session.scalars(
            select(OutboxRecordModel).where(OutboxRecordModel.aggregate_id == red_run_id)
        ).all()

    assert [attempt.status for attempt in attempts] == ["succeeded"]
    assert [proposal.proposal_type for proposal in proposals] == ["http_request"]
    assert [transition.to_state for transition in transitions] == [
        "requested",
        "running",
        "proposal_ready",
    ]
    assert [record.message_type for record in outbox] == ["red.attack_proposed"]
