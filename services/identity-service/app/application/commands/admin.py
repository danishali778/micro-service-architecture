from uuid import uuid4

from app.application.ports.identity_repository import IdentityRepository
from app.application.ports.supabase_auth import SupabaseAuthProvider


class CreateTenant:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    def execute(self, *, tenant_id: str, slug: str, display_name: str) -> None:
        self._repository.create_tenant(
            tenant_id=tenant_id,
            slug=slug,
            display_name=display_name,
        )


class CreateUser:
    def __init__(
        self,
        *,
        repository: IdentityRepository,
        auth_provider: SupabaseAuthProvider,
    ) -> None:
        self._repository = repository
        self._auth_provider = auth_provider

    async def execute(
        self,
        *,
        user_id: str,
        supabase_user_id: str | None,
        email: str,
        display_name: str | None,
        create_supabase_user: bool,
        password: str | None,
    ) -> str:
        resolved_supabase_user_id = supabase_user_id
        if create_supabase_user:
            if password is None:
                raise ValueError("password is required when creating a Supabase user")
            resolved_supabase_user_id = await self._auth_provider.create_user(
                email=email,
                password=password,
            )
        if resolved_supabase_user_id is None:
            resolved_supabase_user_id = user_id

        self._repository.create_user(
            user_id=user_id,
            supabase_user_id=resolved_supabase_user_id,
            email=email,
            display_name=display_name,
        )
        return resolved_supabase_user_id


class AssignMembership:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    def execute(self, *, membership_id: str | None, tenant_id: str, user_id: str) -> str:
        resolved_id = membership_id or _new_id("mbr")
        self._repository.assign_membership(
            membership_id=resolved_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return resolved_id


class AssignRole:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        role_assignment_id: str | None,
        membership_id: str,
        role_code: str,
    ) -> str:
        resolved_id = role_assignment_id or _new_id("roleassign")
        self._repository.assign_role(
            role_assignment_id=resolved_id,
            membership_id=membership_id,
            role_code=role_code,
        )
        return resolved_id


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
