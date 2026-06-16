from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handling import install_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes import health, scenarios
from app.application.ports.scenario_repository import ScenarioRepository
from app.application.queries.list_scenarios import ListScenarios
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.logging import configure_logging
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.health import (
    DatabaseReadinessChecker,
    ReadinessChecker,
)
from app.infrastructure.database.repositories import SqlAlchemyScenarioRepository
from app.security.internal_auth import InternalAuthValidator


def create_app(
    *,
    settings: Settings | None = None,
    scenario_repository: ScenarioRepository | None = None,
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
        resolved_repository = scenario_repository
        resolved_readiness_checker = readiness_checker

        if resolved_repository is None or resolved_readiness_checker is None:
            engine = create_database_engine(resolved_settings)
            session_factory = create_session_factory(engine)
            resolved_repository = resolved_repository or SqlAlchemyScenarioRepository(
                session_factory
            )
            resolved_readiness_checker = resolved_readiness_checker or DatabaseReadinessChecker(
                engine=engine,
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
            )

        application.state.services = Services(
            list_scenarios=ListScenarios(resolved_repository),
            readiness_checker=resolved_readiness_checker,
            internal_auth_validator=resolved_auth_validator,
        )

        yield

        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="Cyber Range Scenario Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    install_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(scenarios.router, prefix=resolved_settings.internal_api_prefix)
    return application


app = create_app()
