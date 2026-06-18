from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.domain.entities.red_run import (
    AgentInfo,
    AttackProposal,
    RedRunOperationResult,
    RedRunRecord,
    RedRunRequest,
    RedScenario,
)
from app.infrastructure.database.connection import SessionFactory
from app.infrastructure.database.models import (
    AttackProposalModel,
    IdempotencyRecordModel,
    OutboxRecordModel,
    RedRunAttemptModel,
    RedRunModel,
    RedRunTransitionModel,
)


class SqlAlchemyRedRunRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def start_red_run(
        self,
        *,
        red_run_id: str,
        tenant_id: str,
        subject_id: str,
        idempotency_key: str,
        request_hash: str,
        request: RedRunRequest,
        adapter_name: str,
        proposal: AttackProposal,
        retention_hours: int,
    ) -> RedRunOperationResult:
        route = "POST /internal/v1/red-runs"
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
                red_run = session.get(RedRunModel, existing.resource_id)
                if red_run is None:
                    raise ConflictError("The original idempotent resource is unavailable.")
                return RedRunOperationResult(
                    red_run=_to_red_run_record(red_run, _proposal_for_run(session, red_run)),
                    status_code=existing.response_status,
                )

            now = datetime.now(UTC)
            red_run = RedRunModel(
                red_run_id=red_run_id,
                tenant_id=tenant_id,
                subject_id=subject_id,
                match_id=request.match_id,
                sandbox_id=request.sandbox_id,
                scenario_snapshot_id=request.scenario.snapshot_id,
                scenario_id=request.scenario.scenario_id,
                scenario_version=request.scenario.version,
                scenario=request.scenario.to_json(),
                target_profile=request.target_profile,
                action_policy=request.action_policy,
                resource_budget=request.resource_budget,
                agent_adapter=adapter_name,
                agent_profile_ref=request.agent_profile_ref,
                state="proposal_ready",
                status_reason="fake_agent_proposal_ready",
                proposal_id=proposal.proposal_id,
                aggregate_version=3,
                created_at=now,
                updated_at=now,
                completed_at=now,
            )
            proposal_model = AttackProposalModel(
                proposal_id=proposal.proposal_id,
                red_run_id=red_run_id,
                proposal_type=proposal.proposal_type,
                title=proposal.title,
                summary=proposal.summary,
                rationale=proposal.rationale,
                action=proposal.action,
                expected_signal=proposal.expected_signal,
                risk_level=proposal.risk_level,
                confidence=str(proposal.confidence),
                validation_status="valid",
                validation_errors=[],
                created_at=now,
            )
            session.add(red_run)
            session.add(proposal_model)
            session.add(
                RedRunAttemptModel(
                    red_run_attempt_id=_new_id("rattempt"),
                    red_run_id=red_run_id,
                    attempt_number=1,
                    adapter=adapter_name,
                    profile_ref=request.agent_profile_ref,
                    state_before="requested",
                    state_after="proposal_ready",
                    status="succeeded",
                    status_reason="fake_agent_proposal_ready",
                    safe_details={},
                    started_at=now,
                    finished_at=now,
                )
            )
            _add_transition(
                session=session,
                red_run_id=red_run_id,
                from_state=None,
                to_state="requested",
                aggregate_version=1,
                reason="red_run_requested",
                actor_subject_id=subject_id,
                now=now,
            )
            _add_transition(
                session=session,
                red_run_id=red_run_id,
                from_state="requested",
                to_state="running",
                aggregate_version=2,
                reason="fake_agent_started",
                actor_subject_id=subject_id,
                now=now,
            )
            _add_transition(
                session=session,
                red_run_id=red_run_id,
                from_state="running",
                to_state="proposal_ready",
                aggregate_version=3,
                reason="fake_agent_proposal_ready",
                actor_subject_id=subject_id,
                now=now,
            )
            _add_outbox(
                session=session,
                message_type="red.attack_proposed",
                red_run=red_run,
                proposal=proposal,
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
                    response_body={"red_run_id": red_run_id},
                    resource_id=red_run_id,
                    retention_hours=retention_hours,
                    now=now,
                )
            )
            session.commit()
            return RedRunOperationResult(
                red_run=_to_red_run_record(red_run, proposal_model),
                status_code=201,
            )

    def get_red_run(
        self,
        *,
        tenant_id: str,
        red_run_id: str,
    ) -> RedRunRecord | None:
        with self._session_factory() as session:
            red_run = session.scalar(
                select(RedRunModel).where(
                    RedRunModel.red_run_id == red_run_id,
                    RedRunModel.tenant_id == tenant_id,
                )
            )
            if red_run is None:
                return None
            return _to_red_run_record(red_run, _proposal_for_run(session, red_run))


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
    red_run_id: str,
    from_state: str | None,
    to_state: str,
    aggregate_version: int,
    reason: str,
    actor_subject_id: str,
    now: datetime,
) -> None:
    session.add(  # type: ignore[attr-defined]
        RedRunTransitionModel(
            red_run_transition_id=_new_id("rtrans"),
            red_run_id=red_run_id,
            from_state=from_state,
            to_state=to_state,
            aggregate_version=aggregate_version,
            reason=reason,
            actor_workload_id="match-orchestrator-service",
            actor_subject_id=actor_subject_id,
            correlation_id="unavailable",
            created_at=now,
        )
    )


def _add_outbox(
    *,
    session: object,
    message_type: str,
    red_run: RedRunModel,
    proposal: AttackProposal,
    now: datetime,
) -> None:
    session.add(  # type: ignore[attr-defined]
        OutboxRecordModel(
            outbox_id=_new_id("outbox"),
            message_id=_new_id("msg"),
            message_type=message_type,
            aggregate_id=red_run.red_run_id,
            aggregate_version=red_run.aggregate_version,
            payload={
                "red_run_id": red_run.red_run_id,
                "tenant_id": red_run.tenant_id,
                "subject_id": red_run.subject_id,
                "match_id": red_run.match_id,
                "sandbox_id": red_run.sandbox_id,
                "state": red_run.state,
                "proposal_id": proposal.proposal_id,
            },
            status="pending",
            attempt_count=0,
            available_at=now,
            created_at=now,
        )
    )


def _proposal_for_run(session: object, red_run: RedRunModel) -> AttackProposalModel | None:
    if red_run.proposal_id is None:
        return None
    return session.get(AttackProposalModel, red_run.proposal_id)  # type: ignore[attr-defined,no-any-return]


def _to_red_run_record(
    red_run: RedRunModel,
    proposal: AttackProposalModel | None,
) -> RedRunRecord:
    return RedRunRecord(
        id=red_run.red_run_id,
        tenant_id=red_run.tenant_id,
        subject_id=red_run.subject_id,
        match_id=red_run.match_id,
        sandbox_id=red_run.sandbox_id,
        scenario=_scenario_from_json(red_run.scenario),
        state=red_run.state,
        status_reason=red_run.status_reason,
        agent=AgentInfo(adapter=red_run.agent_adapter, profile_ref=red_run.agent_profile_ref),
        proposal=_to_attack_proposal(proposal) if proposal is not None else None,
        created_at=red_run.created_at,
        updated_at=red_run.updated_at,
        completed_at=red_run.completed_at,
        failed_at=red_run.failed_at,
    )


def _scenario_from_json(value: dict[str, Any]) -> RedScenario:
    return RedScenario(
        snapshot_id=str(value["snapshot_id"]),
        scenario_id=str(value["scenario_id"]),
        version=str(value["version"]),
        title=str(value["title"]),
    )


def _to_attack_proposal(value: AttackProposalModel) -> AttackProposal:
    return AttackProposal(
        proposal_id=value.proposal_id,
        proposal_type=value.proposal_type,
        title=value.title,
        summary=value.summary,
        rationale=value.rationale,
        action=dict(value.action),
        expected_signal=value.expected_signal,
        risk_level=value.risk_level,
        confidence=float(value.confidence),
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
