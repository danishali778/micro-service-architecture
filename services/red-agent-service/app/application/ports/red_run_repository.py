from typing import Protocol

from app.domain.entities.red_run import (
    AttackProposal,
    RedRunOperationResult,
    RedRunRecord,
    RedRunRequest,
)


class RedRunRepository(Protocol):
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
    ) -> RedRunOperationResult: ...

    def get_red_run(
        self,
        *,
        tenant_id: str,
        red_run_id: str,
    ) -> RedRunRecord | None: ...
