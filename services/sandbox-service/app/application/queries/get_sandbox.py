from dataclasses import dataclass

from app.application.ports.sandbox_repository import SandboxRepository
from app.core.exceptions import NotFoundError
from app.domain.entities.sandbox import SandboxRecord
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class GetSandbox:
    repository: SandboxRepository

    def execute(self, *, sandbox_id: str, context: TrustedInternalContext) -> SandboxRecord:
        sandbox = self.repository.get_sandbox(
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            sandbox_id=sandbox_id,
        )
        if sandbox is None:
            raise NotFoundError()
        return sandbox
