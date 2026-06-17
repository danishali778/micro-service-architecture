from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.entities.match import (
    MatchOperationResult,
    MatchRecord,
    SandboxProvision,
    ScenarioSnapshot,
)
from app.domain.policies.match_lifecycle_policy import TERMINAL_STATES, ensure_cancellable
from app.infrastructure.database.connection import SessionFactory
from app.infrastructure.database.models import (
    IdempotencyRecordModel,
    MatchAttemptModel,
    MatchModel,
    MatchTransitionModel,
    OutboxRecordModel,
)


class SqlAlchemyMatchRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create_match(
        self,
        *,
        match_id: str,
        tenant_id: str,
        subject_id: str,
        idempotency_key: str,
        request_hash: str,
        scenario: ScenarioSnapshot,
        sandbox: SandboxProvision,
        retention_hours: int,
    ) -> MatchOperationResult:
        route = "POST /internal/v1/matches"
        with self._session_factory() as session:
            existing = _find_idempotency_record(
                session=session,
                tenant_id=tenant_id,
                subject_id=subject_id,
                route=route,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                _ensure_same_request(existing, request_hash)
                match = session.get(MatchModel, existing.resource_id)
                if match is None:
                    raise ConflictError("The original idempotent resource is unavailable.")
                return MatchOperationResult(
                    match=_to_match_record(match),
                    status_code=existing.response_status,
                )

            now = datetime.now(UTC)
            match = MatchModel(
                match_id=match_id,
                tenant_id=tenant_id,
                subject_id=subject_id,
                scenario_id=scenario.scenario_id,
                scenario_version=scenario.version,
                scenario_snapshot_id=scenario.snapshot_id,
                scenario_snapshot=scenario.to_json(),
                sandbox_id=sandbox.id,
                sandbox_state=sandbox.state,
                sandbox_provider=sandbox.provider,
                sandbox_allocation=sandbox.allocation,
                state="sandbox_ready",
                phase="setup",
                status_reason="sandbox_ready",
                aggregate_version=2,
                created_at=now,
                updated_at=now,
            )
            session.add(match)
            session.add(
                MatchAttemptModel(
                    match_attempt_id=_new_id("mattempt"),
                    match_id=match_id,
                    attempt_number=1,
                    started_at=now,
                )
            )
            session.add(
                MatchTransitionModel(
                    transition_id=_new_id("mtrans"),
                    match_id=match_id,
                    from_state="created",
                    to_state="waiting_for_sandbox",
                    from_phase="setup",
                    to_phase="setup",
                    aggregate_version=1,
                    caused_by_type="command",
                    caused_by_id=idempotency_key,
                    actor_type="subject",
                    actor_id=subject_id,
                    reason="scenario_snapshot_created",
                    created_at=now,
                )
            )
            session.add(
                MatchTransitionModel(
                    transition_id=_new_id("mtrans"),
                    match_id=match_id,
                    from_state="waiting_for_sandbox",
                    to_state="sandbox_ready",
                    from_phase="setup",
                    to_phase="setup",
                    aggregate_version=2,
                    caused_by_type="sandbox",
                    caused_by_id=sandbox.id,
                    actor_type="workload",
                    actor_id="sandbox-service",
                    reason="sandbox_ready",
                    created_at=now,
                )
            )
            _add_outbox(
                session=session,
                message_type="match.created",
                match=match,
                now=now,
            )
            session.add(
                _idempotency_record(
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_status=201,
                    response_body={"match_id": match_id},
                    resource_id=match_id,
                    retention_hours=retention_hours,
                    now=now,
                )
            )
            session.commit()
            return MatchOperationResult(match=_to_match_record(match), status_code=201)

    def get_match(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        match_id: str,
    ) -> MatchRecord | None:
        with self._session_factory() as session:
            match = session.scalar(
                select(MatchModel).where(
                    MatchModel.match_id == match_id,
                    MatchModel.tenant_id == tenant_id,
                    MatchModel.subject_id == subject_id,
                )
            )
            return _to_match_record(match) if match is not None else None

    def cancel_match(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        match_id: str,
        idempotency_key: str,
        request_hash: str,
        reason: str,
        retention_hours: int,
    ) -> MatchOperationResult:
        route = f"POST /internal/v1/matches/{match_id}/cancel"
        with self._session_factory() as session:
            existing = _find_idempotency_record(
                session=session,
                tenant_id=tenant_id,
                subject_id=subject_id,
                route=route,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                _ensure_same_request(existing, request_hash)
                match = session.get(MatchModel, existing.resource_id)
                if match is None:
                    raise ConflictError("The original idempotent resource is unavailable.")
                return MatchOperationResult(
                    match=_to_match_record(match),
                    status_code=existing.response_status,
                )

            match = session.scalar(
                select(MatchModel).where(
                    MatchModel.match_id == match_id,
                    MatchModel.tenant_id == tenant_id,
                    MatchModel.subject_id == subject_id,
                )
            )
            if match is None:
                raise NotFoundError(
                    code="match_not_found",
                    message="The requested match was not found.",
                )

            ensure_cancellable(match.state)
            now = datetime.now(UTC)
            if match.state not in TERMINAL_STATES:
                previous_state = match.state
                match.state = "cancelling"
                match.status_reason = reason
                match.aggregate_version += 1
                match.updated_at = now
                _add_transition(
                    session=session,
                    match=match,
                    from_state=previous_state,
                    to_state="cancelling",
                    reason=reason,
                    caused_by_id=idempotency_key,
                    actor_id=subject_id,
                    now=now,
                )
                match.state = "cancelled"
                match.cancelled_at = now
                match.aggregate_version += 1
                match.updated_at = now
                _add_transition(
                    session=session,
                    match=match,
                    from_state="cancelling",
                    to_state="cancelled",
                    reason=reason,
                    caused_by_id=idempotency_key,
                    actor_id=subject_id,
                    now=now,
                )
                _add_outbox(
                    session=session,
                    message_type="match.cancelled",
                    match=match,
                    now=now,
                )

            session.add(
                _idempotency_record(
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_status=200,
                    response_body={"match_id": match.match_id},
                    resource_id=match.match_id,
                    retention_hours=retention_hours,
                    now=now,
                )
            )
            session.commit()
            return MatchOperationResult(match=_to_match_record(match), status_code=200)


def _find_idempotency_record(
    *,
    session: object,
    tenant_id: str,
    subject_id: str,
    route: str,
    idempotency_key: str,
) -> IdempotencyRecordModel | None:
    return session.scalar(  # type: ignore[attr-defined,no-any-return]
        select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.tenant_id == tenant_id,
            IdempotencyRecordModel.subject_id == subject_id,
            IdempotencyRecordModel.route == route,
            IdempotencyRecordModel.idempotency_key == idempotency_key,
        )
    )


def _ensure_same_request(record: IdempotencyRecordModel, request_hash: str) -> None:
    if record.request_hash != request_hash:
        raise ConflictError("Idempotency key was already used for a different request.")


def _idempotency_record(
    *,
    tenant_id: str,
    subject_id: str,
    route: str,
    idempotency_key: str,
    request_hash: str,
    response_status: int,
    response_body: dict[str, Any],
    resource_id: str,
    retention_hours: int,
    now: datetime,
) -> IdempotencyRecordModel:
    return IdempotencyRecordModel(
        idempotency_record_id=_new_id("idem"),
        idempotency_key=idempotency_key,
        tenant_id=tenant_id,
        subject_id=subject_id,
        route=route,
        request_hash=request_hash,
        response_status=response_status,
        response_body=response_body,
        resource_id=resource_id,
        expires_at=now + timedelta(hours=retention_hours),
        created_at=now,
    )


def _add_transition(
    *,
    session: object,
    match: MatchModel,
    from_state: str,
    to_state: str,
    reason: str,
    caused_by_id: str,
    actor_id: str,
    now: datetime,
) -> None:
    session.add(  # type: ignore[attr-defined]
        MatchTransitionModel(
            transition_id=_new_id("mtrans"),
            match_id=match.match_id,
            from_state=from_state,
            to_state=to_state,
            from_phase=match.phase,
            to_phase=match.phase,
            aggregate_version=match.aggregate_version,
            caused_by_type="command",
            caused_by_id=caused_by_id,
            actor_type="subject",
            actor_id=actor_id,
            reason=reason,
            created_at=now,
        )
    )


def _add_outbox(
    *,
    session: object,
    message_type: str,
    match: MatchModel,
    now: datetime,
) -> None:
    session.add(  # type: ignore[attr-defined]
        OutboxRecordModel(
            outbox_id=_new_id("outbox"),
            message_id=_new_id("msg"),
            message_type=message_type,
            aggregate_id=match.match_id,
            aggregate_version=match.aggregate_version,
            payload={
                "match_id": match.match_id,
                "tenant_id": match.tenant_id,
                "subject_id": match.subject_id,
                "state": match.state,
                "phase": match.phase,
                "scenario_snapshot_id": match.scenario_snapshot_id,
            },
            status="pending",
            attempt_count=0,
            available_at=now,
            created_at=now,
        )
    )


def _to_match_record(match: MatchModel) -> MatchRecord:
    return MatchRecord(
        id=match.match_id,
        tenant_id=match.tenant_id,
        subject_id=match.subject_id,
        scenario=_snapshot_from_json(match.scenario_snapshot),
        state=match.state,
        phase=match.phase,
        status_reason=match.status_reason,
        created_at=match.created_at,
        updated_at=match.updated_at,
        cancelled_at=match.cancelled_at,
        completed_at=match.completed_at,
        failed_at=match.failed_at,
        sandbox_id=match.sandbox_id,
        sandbox_state=match.sandbox_state,
        sandbox_provider=match.sandbox_provider,
        sandbox_allocation=_dict_or_none(match.sandbox_allocation),
    )


def _snapshot_from_json(value: dict[str, Any]) -> ScenarioSnapshot:
    return ScenarioSnapshot(
        snapshot_id=str(value["snapshot_id"]),
        scenario_id=str(value["scenario_id"]),
        version=str(value["version"]),
        title=str(value["title"]),
        target_profile=_dict_or_empty(value.get("target_profile")),
        runtime_template=_dict_or_empty(value.get("runtime_template")),
        action_policy=_dict_or_empty(value.get("action_policy")),
        resource_budget=_dict_or_empty(value.get("resource_budget")),
        verification_contract=_dict_or_empty(value.get("verification_contract")),
    )


def _dict_or_empty(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _dict_or_none(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return dict(value)
    return None


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
