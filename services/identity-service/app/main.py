from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.error_handling import install_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes import admin, auth, authorization, health
from app.application.commands.admin import AssignMembership, AssignRole, CreateTenant, CreateUser
from app.application.commands.auth import AuthenticateUser, LogoutUserSession, RefreshUserSession
from app.application.ports.identity_repository import IdentityRepository
from app.application.ports.supabase_auth import SupabaseAuthProvider
from app.application.queries.authorization import EvaluateAuthorization
from app.application.queries.session_context import ResolveSessionContext
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.logging import configure_logging
from app.infrastructure.auth.supabase_http_client import SupabaseHttpAuthProvider
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.health import DatabaseReadinessChecker, ReadinessChecker
from app.infrastructure.database.repositories import SqlAlchemyIdentityRepository
from app.security.internal_auth import InternalAuthValidator


def create_app(
    *,
    settings: Settings | None = None,
    repository: IdentityRepository | None = None,
    auth_provider: SupabaseAuthProvider | None = None,
    readiness_checker: ReadinessChecker | None = None,
    internal_auth_validator: InternalAuthValidator | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = None
        http_client: httpx.AsyncClient | None = None
        resolved_auth_validator = internal_auth_validator or InternalAuthValidator(
            resolved_settings
        )
        resolved_repository = repository
        resolved_auth_provider = auth_provider
        resolved_readiness_checker = readiness_checker

        if resolved_repository is None or resolved_readiness_checker is None:
            engine = create_database_engine(resolved_settings)
            session_factory = create_session_factory(engine)
            resolved_repository = resolved_repository or SqlAlchemyIdentityRepository(
                session_factory
            )
            resolved_readiness_checker = resolved_readiness_checker or DatabaseReadinessChecker(
                engine=engine,
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
            )

        if resolved_auth_provider is None:
            timeout = httpx.Timeout(resolved_settings.supabase_request_timeout_ms / 1000)
            http_client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)
            resolved_auth_provider = SupabaseHttpAuthProvider(
                http_client=http_client,
                settings=resolved_settings,
            )

        application.state.services = Services(
            authenticate_user=AuthenticateUser(
                auth_provider=resolved_auth_provider,
                repository=resolved_repository,
            ),
            refresh_user_session=RefreshUserSession(
                auth_provider=resolved_auth_provider,
                repository=resolved_repository,
            ),
            logout_user_session=LogoutUserSession(
                auth_provider=resolved_auth_provider,
                repository=resolved_repository,
            ),
            resolve_session_context=ResolveSessionContext(resolved_repository),
            evaluate_authorization=EvaluateAuthorization(resolved_repository),
            create_tenant=CreateTenant(resolved_repository),
            create_user=CreateUser(
                repository=resolved_repository,
                auth_provider=resolved_auth_provider,
            ),
            assign_membership=AssignMembership(resolved_repository),
            assign_role=AssignRole(resolved_repository),
            readiness_checker=resolved_readiness_checker,
            internal_auth_validator=resolved_auth_validator,
        )

        yield

        if http_client is not None:
            await http_client.aclose()
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="Cyber Range Identity Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    install_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(auth.router, prefix=resolved_settings.internal_api_prefix)
    application.include_router(admin.router, prefix=resolved_settings.internal_api_prefix)
    application.include_router(authorization.router, prefix=resolved_settings.internal_api_prefix)
    return application


app = create_app()
