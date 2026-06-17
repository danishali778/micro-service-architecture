from app.domain.entities.match import SandboxProvision
from app.infrastructure.database.connection import create_session_factory
from app.infrastructure.database.models import Base, MatchTransitionModel, OutboxRecordModel
from app.infrastructure.database.repositories import SqlAlchemyMatchRepository
from conftest import sample_snapshot
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool


def test_repository_records_transitions_and_outbox() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    repository = SqlAlchemyMatchRepository(factory)

    try:
        created = repository.create_match(
            match_id="match_repo_1",
            tenant_id="tenant-1",
            subject_id="subject-1",
            idempotency_key="create-1",
            request_hash="hash-1",
            scenario=sample_snapshot(),
            sandbox=SandboxProvision(
                id="sandbox_123",
                state="ready",
                provider="local_fake",
                allocation={"allocation_id": "local_sandbox_123"},
            ),
            retention_hours=24,
        )
        cancelled = repository.cancel_match(
            tenant_id="tenant-1",
            subject_id="subject-1",
            match_id=created.match.id,
            idempotency_key="cancel-1",
            request_hash="hash-2",
            reason="user_requested",
            retention_hours=24,
        )

        with factory() as session:
            transitions = session.scalars(select(MatchTransitionModel)).all()
            outbox = session.scalars(select(OutboxRecordModel)).all()
    finally:
        engine.dispose()

    assert created.match.state == "sandbox_ready"
    assert created.match.sandbox_id == "sandbox_123"
    assert cancelled.match.state == "cancelled"
    assert [transition.to_state for transition in transitions] == [
        "waiting_for_sandbox",
        "sandbox_ready",
        "cancelling",
        "cancelled",
    ]
    assert [record.message_type for record in outbox] == ["match.created", "match.cancelled"]
