import pytest
from app.core.exceptions import BadGatewayError, ProposalPolicyDeniedError
from app.domain.entities.red_run import AttackProposal
from app.domain.policies.proposal_policy import (
    ensure_policy_allows_proposal,
    validate_proposal_shape,
)


def _proposal(**overrides: object) -> AttackProposal:
    values: dict[str, object] = {
        "proposal_id": "attackprop_1",
        "proposal_type": "http_request",
        "title": "Probe root",
        "summary": "Request root.",
        "rationale": "Safe reconnaissance.",
        "action": {"kind": "http_request", "method": "GET", "path": "/"},
        "expected_signal": "HTTP status.",
        "risk_level": "training_safe",
        "confidence": 0.5,
    }
    values.update(overrides)
    return AttackProposal(**values)  # type: ignore[arg-type]


def test_validate_proposal_rejects_unsupported_type() -> None:
    with pytest.raises(BadGatewayError):
        validate_proposal_shape(_proposal(proposal_type="shell_command"))


def test_validate_proposal_rejects_invalid_action() -> None:
    with pytest.raises(BadGatewayError):
        validate_proposal_shape(_proposal(action={"kind": "http_request", "method": "PUT"}))


def test_validate_proposal_rejects_invalid_confidence() -> None:
    with pytest.raises(BadGatewayError):
        validate_proposal_shape(_proposal(confidence=1.5))


def test_policy_allows_http_when_policy_does_not_restrict_tools() -> None:
    ensure_policy_allows_proposal(
        proposal=_proposal(),
        action_policy={"network": "sandbox-only"},
    )


def test_policy_rejects_network_deny() -> None:
    with pytest.raises(ProposalPolicyDeniedError):
        ensure_policy_allows_proposal(
            proposal=_proposal(),
            action_policy={"network": "deny"},
        )
