import jwt

from app.application.ports.identity_repository import IdentityRepository
from app.application.ports.supabase_auth import SupabaseAuthProvider
from app.core.exceptions import ForbiddenError
from app.domain.entities.identity import AuthTokenSet, SessionContext


class AuthenticateUser:
    def __init__(
        self,
        *,
        auth_provider: SupabaseAuthProvider,
        repository: IdentityRepository,
    ) -> None:
        self._auth_provider = auth_provider
        self._repository = repository

    async def execute(
        self,
        *,
        email: str,
        password: str,
        tenant_id: str,
    ) -> tuple[AuthTokenSet, SessionContext]:
        token_set = await self._auth_provider.login_with_password(email=email, password=password)
        context = self._repository.session_context_for_login(
            supabase_user_id=token_set.supabase_user_id,
            tenant_id=tenant_id,
        )
        if context is None:
            raise ForbiddenError("The user is not allowed to access this tenant.")

        self._repository.record_session(
            supabase_user_id=token_set.supabase_user_id,
            session_id=token_set.session_id,
            tenant_id=context.tenant_id,
            user_id=context.subject_id,
        )
        return token_set, context


class RefreshUserSession:
    def __init__(
        self,
        *,
        auth_provider: SupabaseAuthProvider,
        repository: IdentityRepository,
    ) -> None:
        self._auth_provider = auth_provider
        self._repository = repository

    async def execute(self, *, refresh_token: str) -> tuple[AuthTokenSet, SessionContext]:
        token_set = await self._auth_provider.refresh_session(refresh_token=refresh_token)
        context = self._repository.session_context_for_session(
            supabase_user_id=token_set.supabase_user_id,
            session_id=token_set.session_id,
        )
        if context is None:
            raise ForbiddenError("The refreshed session is not allowed.")

        self._repository.record_session(
            supabase_user_id=token_set.supabase_user_id,
            session_id=token_set.session_id,
            tenant_id=context.tenant_id,
            user_id=context.subject_id,
        )
        return token_set, context


class LogoutUserSession:
    def __init__(
        self,
        *,
        auth_provider: SupabaseAuthProvider,
        repository: IdentityRepository,
    ) -> None:
        self._auth_provider = auth_provider
        self._repository = repository

    async def execute(self, *, access_token: str) -> None:
        supabase_user_id, session_id = _claims_identity(access_token)
        await self._auth_provider.logout(access_token=access_token)
        self._repository.revoke_session(
            supabase_user_id=supabase_user_id,
            session_id=session_id,
        )


def _claims_identity(access_token: str) -> tuple[str, str]:
    claims = jwt.decode(
        access_token,
        options={
            "verify_signature": False,
            "verify_aud": False,
            "verify_exp": False,
            "verify_nbf": False,
            "verify_iat": False,
        },
    )
    subject = claims.get("sub")
    session_id = claims.get("session_id")
    if not isinstance(subject, str) or not isinstance(session_id, str):
        raise ForbiddenError("The session token is not valid for logout.")
    return subject, session_id
