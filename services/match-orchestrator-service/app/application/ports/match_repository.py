from typing import Protocol

from app.domain.entities.match import (
    MatchOperationResult,
    MatchRecord,
    RedRunResult,
    SandboxProvision,
    ScenarioSnapshot,
)


class MatchRepository(Protocol):
    def ensure_sandbox_ready_match(
        self,
        *,
        match_id: str,
        tenant_id: str,
        subject_id: str,
        idempotency_key: str,
        request_hash: str,
        scenario: ScenarioSnapshot,
        sandbox: SandboxProvision,
    ) -> MatchOperationResult: ...

    def mark_red_proposal_ready(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        match_id: str,
        idempotency_key: str,
        request_hash: str,
        red_run: RedRunResult,
        retention_hours: int,
    ) -> MatchOperationResult: ...

    def get_match(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        match_id: str,
    ) -> MatchRecord | None: ...

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
    ) -> MatchOperationResult: ...
