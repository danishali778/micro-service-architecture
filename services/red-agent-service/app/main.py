from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handling import install_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes import health, red_runs
from app.application.commands.start_red_run import StartRedRun
from app.application.ports.agent import RedAgent
from app.application.ports.red_run_repository import RedRunRepository
from app.application.queries.get_red_run import GetRedRun
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.logging import configure_logging
from app.infrastructure.agents.local_fake_agent import LocalFakeRedAgent
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.health import DatabaseReadinessChecker, ReadinessChecker
from app.infrastructure.database.repositories import SqlAlchemyRedRunRepository
from app.security.internal_auth import InternalAuthValidator


def create_app(
    *,
    settings: Settings | None = None,
    red_run_repository: RedRunRepository | None = None,
    agent: RedAgent | None = None,
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
        resolved_repository = red_run_repository
        resolved_agent = agent or LocalFakeRedAgent()
        resolved_readiness_checker = readiness_checker

        if resolved_repository is None:
            engine = create_database_engine(resolved_settings)
            session_factory = create_session_factory(engine)
            resolved_repository = SqlAlchemyRedRunRepository(session_factory)
            resolved_readiness_checker = resolved_readiness_checker or DatabaseReadinessChecker(
                engine=engine,
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
                agent=resolved_agent,
            )

        if resolved_readiness_checker is None:
            resolved_readiness_checker = DatabaseReadinessChecker(
                engine=create_database_engine(resolved_settings),
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
                agent=resolved_agent,
            )

        application.state.services = Services(
            start_red_run=StartRedRun(
                repository=resolved_repository,
                agent=resolved_agent,
                settings=resolved_settings,
            ),
            get_red_run=GetRedRun(resolved_repository),
            readiness_checker=resolved_readiness_checker,
            internal_auth_validator=resolved_auth_validator,
        )

        yield

        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="Cyber Range Red Agent Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    install_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(red_runs.router, prefix=resolved_settings.internal_api_prefix)
    return application


app = create_app()
