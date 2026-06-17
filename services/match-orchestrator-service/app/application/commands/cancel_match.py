from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.application.ports.match_repository import MatchRepository
from app.application.ports.sandbox_client import SandboxClient
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.entities.match import MatchOperationResult
from app.domain.policies.match_lifecycle_policy import TERMINAL_STATES
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class CancelMatch:
    repository: MatchRepository
    sandbox_client: SandboxClient
    settings: Settings

    async def execute(
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
            match = self.repository.get_match(
                tenant_id=context.tenant_id,
                subject_id=context.subject_id,
                match_id=match_id,
            )
            if match is None:
                raise NotFoundError(
                    code="match_not_found",
                    message="The requested match was not found.",
                )
            if match.sandbox_id is not None and match.state not in TERMINAL_STATES:
                await self.sandbox_client.terminate_sandbox(
                    sandbox_id=match.sandbox_id,
                    reason=reason,
                    idempotency_key=idempotency_key,
                    context=context,
                )
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
