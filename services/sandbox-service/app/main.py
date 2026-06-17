from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handling import install_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes import health, sandboxes
from app.application.commands.provision_sandbox import ProvisionSandbox
from app.application.commands.terminate_sandbox import TerminateSandbox
from app.application.ports.provider import SandboxProvider
from app.application.ports.sandbox_repository import SandboxRepository
from app.application.queries.get_sandbox import GetSandbox
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.logging import configure_logging
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.health import DatabaseReadinessChecker, ReadinessChecker
from app.infrastructure.database.repositories import SqlAlchemySandboxRepository
from app.infrastructure.providers.local_fake_provider import LocalFakeSandboxProvider
from app.security.internal_auth import InternalAuthValidator


def create_app(
    *,
    settings: Settings | None = None,
    sandbox_repository: SandboxRepository | None = None,
    provider: SandboxProvider | None = None,
    readiness_checker: ReadinessChecker | None = None,
    internal_auth_validator: InternalAuthValidator | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = None
        resolved_auth_validator = internal_auth_validator or InternalAuthValidator(
            resolved_settings
        )
        resolved_provider = provider or _provider_from_settings(resolved_settings)
        resolved_repository = sandbox_repository
        resolved_readiness_checker = readiness_checker

        if resolved_repository is None:
            engine = create_database_engine(resolved_settings)
            session_factory = create_session_factory(engine)
            resolved_repository = SqlAlchemySandboxRepository(session_factory)
            resolved_readiness_checker = resolved_readiness_checker or DatabaseReadinessChecker(
                engine=engine,
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
                provider=resolved_provider,
            )

        if resolved_readiness_checker is None:
            resolved_readiness_checker = DatabaseReadinessChecker(
                engine=create_database_engine(resolved_settings),
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
                provider=resolved_provider,
            )

        application.state.services = Services(
            provision_sandbox=ProvisionSandbox(
                repository=resolved_repository,
                provider=resolved_provider,
                settings=resolved_settings,
            ),
            get_sandbox=GetSandbox(resolved_repository),
            terminate_sandbox=TerminateSandbox(
                repository=resolved_repository,
                provider=resolved_provider,
                settings=resolved_settings,
            ),
            readiness_checker=resolved_readiness_checker,
            internal_auth_validator=resolved_auth_validator,
        )

        yield

        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="Cyber Range Sandbox Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    install_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(sandboxes.router, prefix=resolved_settings.internal_api_prefix)
    return application


def _provider_from_settings(settings: Settings) -> SandboxProvider:
    if settings.sandbox_provider == "local_fake":
        return LocalFakeSandboxProvider()
    from app.core.exceptions import ServiceUnavailableError

    raise ServiceUnavailableError(
        "Sandbox provider is not configured.",
        code="sandbox_provider_unconfigured",
    )


app = create_app()
