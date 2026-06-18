from typing import Any

from app.core.exceptions import BadGatewayError, ProposalPolicyDeniedError
from app.domain.entities.red_run import AttackProposal

TERMINAL_STATES = frozenset(
    {"proposal_ready", "proposal_rejected", "failed", "cancelled", "timed_out"}
)


def validate_proposal_shape(proposal: AttackProposal) -> None:
    if proposal.proposal_type != "http_request":
        raise BadGatewayError("Agent output used an unsupported proposal type.")
    action = proposal.action
    if action.get("kind") != "http_request":
        raise BadGatewayError("Agent output used an unsupported action kind.")
    method = action.get("method")
    path = action.get("path")
    if method not in {"GET", "POST"} or not isinstance(path, str) or not path.startswith("/"):
        raise BadGatewayError("Agent output is not a valid HTTP request proposal.")
    if not 0 <= proposal.confidence <= 1:
        raise BadGatewayError("Agent output confidence is invalid.")


def ensure_policy_allows_proposal(
    *,
    proposal: AttackProposal,
    action_policy: dict[str, Any],
) -> None:
    allowed_tools = action_policy.get("allowed_tools")
    if isinstance(allowed_tools, list) and "http" not in {str(item) for item in allowed_tools}:
        raise ProposalPolicyDeniedError()

    network = action_policy.get("network")
    network_egress = action_policy.get("network_egress")
    if network == "deny" or network_egress == "deny":
        raise ProposalPolicyDeniedError()

    action = proposal.action
    if action.get("kind") != "http_request":
        raise ProposalPolicyDeniedError()
