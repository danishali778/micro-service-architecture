from app.application.ports.identity_repository import IdentityRepository
from app.core.exceptions import UnauthorizedError
from app.domain.entities.identity import SessionContext


class ResolveSessionContext:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    def execute(self, *, supabase_user_id: str, session_id: str) -> SessionContext:
        context = self._repository.session_context_for_session(
            supabase_user_id=supabase_user_id,
            session_id=session_id,
        )
        if context is None:
            raise UnauthorizedError("The session is not known to the platform.")
        return context
