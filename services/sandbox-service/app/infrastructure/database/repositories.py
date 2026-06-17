from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.domain.entities.sandbox import (
    CleanupResult,
    ProviderAllocation,
    SandboxOperationResult,
    SandboxRecord,
    SandboxScenario,
)
from app.domain.policies.sandbox_lifecycle_policy import TERMINAL_STATES, ensure_terminatable
from app.infrastructure.database.connection import SessionFactory
from app.infrastructure.database.models import (
    IdempotencyRecordModel,
    OutboxRecordModel,
    SandboxAttemptModel,
    SandboxModel,
    SandboxTransitionModel,
)


class SqlAlchemySandboxRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def provision_sandbox(
        self,
        *,
        sandbox_id: str,
        tenant_id: str,
        subject_id: str,
        match_id: str,
        scenario: SandboxScenario,
        runtime_template: dict[str, Any],
        action_policy: dict[str, Any],
        resource_budget: dict[str, Any],
        lease_duration_seconds: int,
        provider_name: str,
        allocation: ProviderAllocation,
        idempotency_key: str,
        request_hash: str,
        retention_hours: int,
    ) -> SandboxOperationResult:
        route = "POST /internal/v1/sandboxes"
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
                sandbox = session.get(SandboxModel, existing.resource_id)
                if sandbox is None:
                    raise ConflictError("The original idempotent resource is unavailable.")
                return SandboxOperationResult(
                    sandbox=_to_sandbox_record(sandbox),
                    status_code=existing.response_status,
                )

            now = datetime.now(UTC)
            allocation_json = allocation.to_json()
            sandbox = SandboxModel(
                sandbox_id=sandbox_id,
                tenant_id=tenant_id,
                subject_id=subject_id,
                match_id=match_id,
                scenario_snapshot_id=scenario.snapshot_id,
                scenario_id=scenario.scenario_id,
                scenario_version=scenario.version,
                scenario=scenario.to_json(),
                state="ready",
                status_reason="local_provider_ready",
                provider=provider_name,
                runtime_template=runtime_template,
                action_policy=action_policy,
                resource_budget=resource_budget,
                allocation=allocation_json,
                aggregate_version=3,
                lease_expires_at=now + timedelta(seconds=lease_duration_seconds),
                created_at=now,
                updated_at=now,
                ready_at=now,
            )
            session.add(sandbox)
            session.add(
                SandboxAttemptModel(
                    sandbox_attempt_id=_new_id("sattempt"),
                    sandbox_id=sandbox_id,
                    attempt_type="provision",
                    attempt_number=1,
                    provider=provider_name,
                    state_before="requested",
                    state_after="ready",
                    status="succeeded",
                    status_reason="local_provider_ready",
                    safe_details={},
                    started_at=now,
                    finished_at=now,
                )
            )
            _add_transition(
                session=session,
                sandbox_id=sandbox_id,
                from_state=None,
                to_state="requested",
                aggregate_version=1,
                reason="provision_requested",
                caused_by_id=idempotency_key,
                actor_subject_id=subject_id,
                now=now,
            )
            _add_transition(
                session=session,
                sandbox_id=sandbox_id,
                from_state="requested",
                to_state="provisioning",
                aggregate_version=2,
                reason="provider_provisioning_started",
                caused_by_id=idempotency_key,
                actor_subject_id=subject_id,
                now=now,
            )
            _add_transition(
                session=session,
                sandbox_id=sandbox_id,
                from_state="provisioning",
                to_state="ready",
                aggregate_version=3,
                reason="local_provider_ready",
                caused_by_id=idempotency_key,
                actor_subject_id=subject_id,
                now=now,
            )
            _add_outbox(
                session=session,
                message_type="sandbox.ready",
                sandbox=sandbox,
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
                    response_body={"sandbox_id": sandbox_id},
                    resource_id=sandbox_id,
                    retention_hours=retention_hours,
                    now=now,
                )
            )
            session.commit()
            return SandboxOperationResult(sandbox=_to_sandbox_record(sandbox), status_code=201)

    def get_sandbox(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        sandbox_id: str,
    ) -> SandboxRecord | None:
        with self._session_factory() as session:
            sandbox = session.scalar(
                select(SandboxModel).where(
                    SandboxModel.sandbox_id == sandbox_id,
                    SandboxModel.tenant_id == tenant_id,
                    SandboxModel.subject_id == subject_id,
                )
            )
            return _to_sandbox_record(sandbox) if sandbox is not None else None

    def terminate_sandbox(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        sandbox_id: str,
        reason: str,
        cleanup: CleanupResult,
        idempotency_key: str,
        request_hash: str,
        retention_hours: int,
    ) -> SandboxOperationResult:
        route = f"POST /internal/v1/sandboxes/{sandbox_id}/terminate"
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
                sandbox = session.get(SandboxModel, existing.resource_id)
                if sandbox is None:
                    raise ConflictError("The original idempotent resource is unavailable.")
                return SandboxOperationResult(
                    sandbox=_to_sandbox_record(sandbox),
                    status_code=existing.response_status,
                )

            sandbox = session.scalar(
                select(SandboxModel).where(
                    SandboxModel.sandbox_id == sandbox_id,
                    SandboxModel.tenant_id == tenant_id,
                    SandboxModel.subject_id == subject_id,
                )
            )
            if sandbox is None:
                from app.core.exceptions import NotFoundError

                raise NotFoundError()

            ensure_terminatable(sandbox.state)
            now = datetime.now(UTC)
            if sandbox.state not in TERMINAL_STATES:
                previous_state = sandbox.state
                sandbox.state = "termination_requested"
                sandbox.status_reason = reason
                sandbox.aggregate_version += 1
                sandbox.updated_at = now
                _add_transition(
                    session=session,
                    sandbox_id=sandbox_id,
                    from_state=previous_state,
                    to_state="termination_requested",
                    aggregate_version=sandbox.aggregate_version,
                    reason=reason,
                    caused_by_id=idempotency_key,
                    actor_subject_id=subject_id,
                    now=now,
                )
                sandbox.state = "terminating"
                sandbox.aggregate_version += 1
                sandbox.updated_at = now
                _add_transition(
                    session=session,
                    sandbox_id=sandbox_id,
                    from_state="termination_requested",
                    to_state="terminating",
                    aggregate_version=sandbox.aggregate_version,
                    reason=reason,
                    caused_by_id=idempotency_key,
                    actor_subject_id=subject_id,
                    now=now,
                )
                sandbox.state = "terminated"
                sandbox.cleanup = cleanup.to_json()
                sandbox.terminated_at = now
                sandbox.aggregate_version += 1
                sandbox.updated_at = now
                _add_transition(
                    session=session,
                    sandbox_id=sandbox_id,
                    from_state="terminating",
                    to_state="terminated",
                    aggregate_version=sandbox.aggregate_version,
                    reason=reason,
                    caused_by_id=idempotency_key,
                    actor_subject_id=subject_id,
                    now=now,
                )
                _add_outbox(
                    session=session,
                    message_type="sandbox.terminated",
                    sandbox=sandbox,
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
                    response_body={"sandbox_id": sandbox_id},
                    resource_id=sandbox_id,
                    retention_hours=retention_hours,
                    now=now,
                )
            )
            session.commit()
            return SandboxOperationResult(sandbox=_to_sandbox_record(sandbox), status_code=200)


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
    sandbox_id: str,
    from_state: str | None,
    to_state: str,
    aggregate_version: int,
    reason: str,
    caused_by_id: str,
    actor_subject_id: str,
    now: datetime,
) -> None:
    session.add(  # type: ignore[attr-defined]
        SandboxTransitionModel(
            sandbox_transition_id=_new_id("strans"),
            sandbox_id=sandbox_id,
            from_state=from_state,
            to_state=to_state,
            aggregate_version=aggregate_version,
            caused_by_type="command",
            caused_by_id=caused_by_id,
            actor_workload_id="match-orchestrator-service",
            actor_subject_id=actor_subject_id,
            reason=reason,
            created_at=now,
        )
    )


def _add_outbox(
    *,
    session: object,
    message_type: str,
    sandbox: SandboxModel,
    now: datetime,
) -> None:
    session.add(  # type: ignore[attr-defined]
        OutboxRecordModel(
            outbox_id=_new_id("outbox"),
            message_id=_new_id("msg"),
            message_type=message_type,
            aggregate_id=sandbox.sandbox_id,
            aggregate_version=sandbox.aggregate_version,
            payload={
                "sandbox_id": sandbox.sandbox_id,
                "tenant_id": sandbox.tenant_id,
                "subject_id": sandbox.subject_id,
                "match_id": sandbox.match_id,
                "state": sandbox.state,
                "provider": sandbox.provider,
            },
            status="pending",
            attempt_count=0,
            available_at=now,
            created_at=now,
        )
    )


def _to_sandbox_record(sandbox: SandboxModel) -> SandboxRecord:
    return SandboxRecord(
        id=sandbox.sandbox_id,
        tenant_id=sandbox.tenant_id,
        subject_id=sandbox.subject_id,
        match_id=sandbox.match_id,
        scenario=_scenario_from_json(sandbox.scenario),
        state=sandbox.state,
        status_reason=sandbox.status_reason,
        provider=sandbox.provider,
        allocation=dict(sandbox.allocation),
        lease_expires_at=sandbox.lease_expires_at,
        created_at=sandbox.created_at,
        updated_at=sandbox.updated_at,
        ready_at=sandbox.ready_at,
        terminated_at=sandbox.terminated_at,
        failed_at=sandbox.failed_at,
        cleanup=_cleanup_from_json(sandbox.cleanup),
    )


def _scenario_from_json(value: dict[str, Any]) -> SandboxScenario:
    return SandboxScenario(
        snapshot_id=str(value["snapshot_id"]),
        scenario_id=str(value["scenario_id"]),
        version=str(value["version"]),
        title=str(value["title"]),
    )


def _cleanup_from_json(value: dict[str, Any] | None) -> CleanupResult | None:
    if value is None:
        return None
    details = value.get("details")
    return CleanupResult(
        status=str(value.get("status", "completed")),
        details=details if isinstance(details, list) else [],
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
