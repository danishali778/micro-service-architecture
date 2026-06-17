from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.application.ports.provider import SandboxProvider
from app.application.ports.sandbox_repository import SandboxRepository
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.entities.sandbox import SandboxOperationResult
from app.domain.policies.sandbox_lifecycle_policy import TERMINAL_STATES
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class TerminateSandbox:
    repository: SandboxRepository
    provider: SandboxProvider
    settings: Settings

    def execute(
        self,
        *,
        sandbox_id: str,
        reason: str,
        idempotency_key: str,
        context: TrustedInternalContext,
    ) -> SandboxOperationResult:
        request_hash = _request_hash(
            {
                "operation": "terminate_sandbox",
                "sandbox_id": sandbox_id,
                "reason": reason,
            }
        )
        sandbox = self.repository.get_sandbox(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            sandbox_id=sandbox_id,
        )
        if sandbox is None:
            raise NotFoundError()

        if sandbox.state in TERMINAL_STATES:
            cleanup = sandbox.cleanup or self.provider.terminate(allocation=sandbox.allocation)
        else:
            cleanup = self.provider.terminate(allocation=sandbox.allocation)

        return self.repository.terminate_sandbox(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            sandbox_id=sandbox_id,
            reason=reason,
            cleanup=cleanup,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            retention_hours=self.settings.idempotency_retention_hours,
        )


def _request_hash(payload: dict[str, object]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()
