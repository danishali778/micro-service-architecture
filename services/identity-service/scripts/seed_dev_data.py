import os
from collections.abc import Callable
from dataclasses import dataclass

from app.core.config import Settings
from app.core.exceptions import ConflictError
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.repositories import SqlAlchemyIdentityRepository


@dataclass(frozen=True, slots=True)
class SeedConfig:
    tenant_id: str = "tenant_demo"
    user_id: str = "user_demo"
    supabase_user_id: str = "supabase_user_demo"
    email: str = "learner@example.com"
    membership_id: str = "mbr_demo"
    role_assignment_id: str = "roleassign_demo"


def main() -> None:
    settings = Settings()
    config = SeedConfig(
        tenant_id=os.getenv("DEV_TENANT_ID", "tenant_demo"),
        user_id=os.getenv("DEV_USER_ID", "user_demo"),
        supabase_user_id=os.getenv("DEV_SUPABASE_USER_ID", "supabase_user_demo"),
        email=os.getenv("DEV_USER_EMAIL", "learner@example.com"),
    )

    engine = create_database_engine(settings)
    try:
        repository = SqlAlchemyIdentityRepository(create_session_factory(engine))
        repository.create_role(
            role_code="security_learner",
            display_name="Security Learner",
            scopes=frozenset(
                {
                    "scenarios:read",
                    "matches:create",
                    "matches:read",
                    "matches:cancel",
                }
            ),
        )
        _try(
            lambda: repository.create_tenant(
                tenant_id=config.tenant_id,
                slug=config.tenant_id,
                display_name="Demo Tenant",
            )
        )
        _try(
            lambda: repository.create_user(
                user_id=config.user_id,
                supabase_user_id=config.supabase_user_id,
                email=config.email,
                display_name="Demo Learner",
            )
        )
        _try(
            lambda: repository.assign_membership(
                membership_id=config.membership_id,
                tenant_id=config.tenant_id,
                user_id=config.user_id,
            )
        )
        _try(
            lambda: repository.assign_role(
                role_assignment_id=config.role_assignment_id,
                membership_id=config.membership_id,
                role_code="security_learner",
            )
        )
    finally:
        engine.dispose()


def _try(operation: Callable[[], None]) -> None:
    try:
        operation()
    except ConflictError:
        return


if __name__ == "__main__":
    main()
