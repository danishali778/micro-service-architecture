from dataclasses import dataclass

from app.application.ports.match_repository import MatchRepository
from app.core.exceptions import NotFoundError
from app.domain.entities.match import MatchRecord
from app.security.internal_auth import TrustedInternalContext


@dataclass(frozen=True, slots=True)
class GetMatch:
    repository: MatchRepository

    def execute(
        self,
        *,
        match_id: str,
        context: TrustedInternalContext,
    ) -> MatchRecord:
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
        return match
