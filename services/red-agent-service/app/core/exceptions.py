from http import HTTPStatus
from typing import Any


class RedAgentError(Exception):
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class AuthenticationError(RedAgentError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "missing_internal_auth"
    message = "Internal authentication is required or invalid."


class AuthorizationError(RedAgentError):
    status_code = HTTPStatus.FORBIDDEN
    code = "missing_scope"
    message = "The caller is not allowed to perform this operation."


class NotFoundError(RedAgentError):
    status_code = HTTPStatus.NOT_FOUND
    code = "red_run_not_found"
    message = "The requested red run was not found."


class ConflictError(RedAgentError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"
    message = "The requested operation conflicts with current state."


class ProposalPolicyDeniedError(ConflictError):
    code = "proposal_policy_denied"
    message = "The generated proposal is not allowed by policy."


class BadGatewayError(RedAgentError):
    status_code = HTTPStatus.BAD_GATEWAY
    code = "invalid_agent_output"
    message = "A required agent returned an invalid response."


class ServiceUnavailableError(RedAgentError):
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    code = "agent_unavailable"
    message = "A required agent is unavailable."


class GatewayTimeoutError(RedAgentError):
    status_code = HTTPStatus.GATEWAY_TIMEOUT
    code = "agent_timeout"
    message = "A required agent did not respond in time."
