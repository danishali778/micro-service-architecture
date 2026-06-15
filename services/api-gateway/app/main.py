from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handling import install_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes import health, scenarios
from app.application.ports.internal_auth import InternalAuthenticator
from app.application.ports.scenario_client import ScenarioClient
from app.application.queries.list_scenarios import ListScenarios
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.logging import configure_logging
from app.infrastructure.clients.deferred_internal_auth import DeferredInternalAuthenticator
from app.infrastructure.clients.local_internal_auth import LocalHeaderAuthenticator
from app.infrastructure.clients.scenario_http_client import ScenarioHttpClient
from app.infrastructure.oidc.token_validator import OidcTokenValidator
from app.security.token_validator import TokenValidator

logger = structlog.get_logger()


def create_app(
    *,
    settings: Settings | None = None,
    token_validator: TokenValidator | None = None,
    scenario_client: ScenarioClient | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        timeout = httpx.Timeout(
            connect=resolved_settings.downstream_connect_timeout_ms / 1000,
            read=resolved_settings.downstream_request_timeout_ms / 1000,
            write=resolved_settings.downstream_request_timeout_ms / 1000,
            pool=resolved_settings.downstream_connect_timeout_ms / 1000,
        )
        http_client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)
        resolved_token_validator = token_validator or OidcTokenValidator(
            settings=resolved_settings,
            http_client=http_client,
        )

        internal_authenticator: InternalAuthenticator
        if resolved_settings.internal_auth_mode == "local_header":
            internal_authenticator = LocalHeaderAuthenticator()
        else:
            internal_authenticator = DeferredInternalAuthenticator()
        resolved_scenario_client = scenario_client or ScenarioHttpClient(
            http_client=http_client,
            base_url=str(resolved_settings.scenario_service_url),
            authenticator=internal_authenticator,
        )
        application.state.services = Services(
            token_validator=resolved_token_validator,
            list_scenarios=ListScenarios(resolved_scenario_client),
        )

        try:
            await resolved_token_validator.initialize()
        except (httpx.HTTPError, ValueError, KeyError) as error:
            await logger.awarning(
                "oidc_initialization_failed",
                error_type=type(error).__name__,
            )

        yield
        await http_client.aclose()

    application = FastAPI(
        title="Cyber Range API Gateway",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Authorization", "X-Correlation-ID"],
    )
    install_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(scenarios.router, prefix=resolved_settings.public_api_prefix)
    return application


app = create_app()
