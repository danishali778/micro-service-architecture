from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import RedAgentError


def install_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RedAgentError)
    async def red_agent_error_handler(
        request: Request,
        error: RedAgentError,
    ) -> JSONResponse:
        return _error_response(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            correlation_id=_correlation_id(request),
            details=error.details,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="The request is invalid.",
            correlation_id=_correlation_id(request),
            details=[
                {
                    "field": ".".join(str(part) for part in item["loc"]),
                    "message": str(item["msg"]),
                }
                for item in error.errors()
            ],
        )

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
        _ = error
        return _error_response(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="An unexpected error occurred.",
            correlation_id=_correlation_id(request),
            details=[],
        )


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", "unavailable"))


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
    details: list[dict[str, Any]],
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id,
                "details": details,
            }
        },
    )
