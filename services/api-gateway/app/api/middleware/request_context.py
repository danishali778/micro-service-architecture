import time
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.error_handling import unexpected_error_response
from app.domain.value_objects.correlation_id import CorrelationId

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = CorrelationId.from_untrusted(request.headers.get("X-Correlation-ID")).value
        request.state.correlation_id = correlation_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as error:
            response = await unexpected_error_response(request, error)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"

        route = request.scope.get("route")
        route_template = getattr(route, "path", request.url.path)
        await logger.ainfo(
            "request_complete",
            method=request.method,
            route=route_template,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        return response
