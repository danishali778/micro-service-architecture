from dataclasses import dataclass

from app.application.ports.red_run_repository import RedRunRepository
from app.core.exceptions import NotFoundError
from app.domain.entities.red_run import RedRunRecord
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class GetRedRun:
    repository: RedRunRepository

    def execute(self, *, red_run_id: str, context: TrustedInternalContext) -> RedRunRecord:
        red_run = self.repository.get_red_run(
            tenant_id=context.tenant_id,
            red_run_id=red_run_id,
        )
        if red_run is None:
            raise NotFoundError()
        return red_run
