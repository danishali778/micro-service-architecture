from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.application.ports.match_repository import MatchRepository
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.entities.match import MatchOperationResult
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class CancelMatch:
    repository: MatchRepository
    settings: Settings

    def execute(
        self,
        *,
        match_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> MatchOperationResult:
        request_hash = _request_hash(
            {
                "operation": "cancel_match",
                "match_id": match_id,
                "reason": reason,
            }
        )
        try:
            return self.repository.cancel_match(
                tenant_id=context.tenant_id,
                subject_id=context.subject_id,
                match_id=match_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                reason=reason,
                retention_hours=self.settings.idempotency_retention_hours,
            )
        except NotFoundError:
            raise


def _request_hash(payload: dict[str, object]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()
