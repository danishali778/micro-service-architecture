from typing import Protocol

from app.domain.entities.match import MatchOperationResult, MatchRecord, ScenarioSnapshot


class MatchRepository(Protocol):
    def create_match(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        idempotency_key: str,
        request_hash: str,
        scenario: ScenarioSnapshot,
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
