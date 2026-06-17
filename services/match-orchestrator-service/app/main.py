from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.error_handling import install_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes import health, matches
from app.application.commands.cancel_match import CancelMatch
from app.application.commands.create_match import CreateMatch
from app.application.ports.match_repository import MatchRepository
from app.application.ports.sandbox_client import SandboxClient
from app.application.ports.scenario_client import ScenarioClient
from app.application.queries.get_match import GetMatch
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.logging import configure_logging
from app.infrastructure.clients.sandbox_http_client import SandboxHttpClient
from app.infrastructure.clients.scenario_http_client import ScenarioHttpClient
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.health import DatabaseReadinessChecker, ReadinessChecker
from app.infrastructure.database.repositories import SqlAlchemyMatchRepository
from app.security.internal_auth import InternalAuthValidator


def create_app(
    *,
    settings: Settings | None = None,
    match_repository: MatchRepository | None = None,
    scenario_client: ScenarioClient | None = None,
    sandbox_client: SandboxClient | None = None,
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
        resolved_repository = match_repository
        resolved_scenario_client = scenario_client
        resolved_sandbox_client = sandbox_client
        resolved_readiness_checker = readiness_checker

        if resolved_repository is None:
            engine = create_database_engine(resolved_settings)
            session_factory = create_session_factory(engine)
            resolved_repository = SqlAlchemyMatchRepository(session_factory)
            resolved_readiness_checker = resolved_readiness_checker or DatabaseReadinessChecker(
                engine=engine,
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
            )

        if resolved_scenario_client is None or resolved_sandbox_client is None:
            timeout = httpx.Timeout(
                connect=resolved_settings.downstream_connect_timeout_ms / 1000,
                read=resolved_settings.downstream_request_timeout_ms / 1000,
                write=resolved_settings.downstream_request_timeout_ms / 1000,
                pool=resolved_settings.downstream_connect_timeout_ms / 1000,
            )
            http_client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)
        if resolved_scenario_client is None:
            assert http_client is not None
            resolved_scenario_client = ScenarioHttpClient(
                http_client=http_client,
                base_url=str(resolved_settings.scenario_service_url),
            )
        if resolved_sandbox_client is None:
            assert http_client is not None
            resolved_sandbox_client = SandboxHttpClient(
                http_client=http_client,
                base_url=str(resolved_settings.sandbox_service_url),
            )

        if resolved_readiness_checker is None:
            resolved_readiness_checker = DatabaseReadinessChecker(
                engine=create_database_engine(resolved_settings),
                settings=resolved_settings,
                internal_auth_validator=resolved_auth_validator,
            )

        application.state.services = Services(
            create_match=CreateMatch(
                repository=resolved_repository,
                scenario_client=resolved_scenario_client,
                sandbox_client=resolved_sandbox_client,
                settings=resolved_settings,
            ),
            get_match=GetMatch(resolved_repository),
            cancel_match=CancelMatch(
                repository=resolved_repository,
                sandbox_client=resolved_sandbox_client,
                settings=resolved_settings,
            ),
            readiness_checker=resolved_readiness_checker,
            internal_auth_validator=resolved_auth_validator,
        )

        yield

        if http_client is not None:
            await http_client.aclose()
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="Cyber Range Match Orchestrator Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    install_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(matches.router, prefix=resolved_settings.internal_api_prefix)
    return application


app = create_app()
