from hashlib import sha256
from typing import Any

from app.domain.entities.red_run import AttackProposal, RedRunRequest


class LocalFakeRedAgent:
    adapter_name = "local_fake"
    is_ready = True

    async def generate_proposal(self, request: RedRunRequest) -> AttackProposal:
        proposal_id = _proposal_id(request)
        if request.scenario.scenario_id == "scn_sql_injection_login":
            return AttackProposal(
                proposal_id=proposal_id,
                proposal_type="http_request",
                title="Probe login form for SQL injection",
                summary="Submit a controlled authentication bypass payload to the login form.",
                rationale="The scenario target is a login bypass training target.",
                action={
                    "kind": "http_request",
                    "method": "POST",
                    "path": "/login",
                    "body_template": {
                        "username": "admin' OR '1'='1",
                        "password": "anything",
                    },
                },
                expected_signal="Authenticated response or role-bearing session cookie.",
                risk_level="training_safe",
                confidence=0.75,
            )
        return AttackProposal(
            proposal_id=proposal_id,
            proposal_type="http_request",
            title="Inspect target root route",
            summary="Request the target root route to identify the application surface.",
            rationale="A bounded HTTP request is a safe first reconnaissance proposal.",
            action={"kind": "http_request", "method": "GET", "path": "/"},
            expected_signal="HTTP status, headers, and landing page content.",
            risk_level="training_safe",
            confidence=0.6,
        )


def _proposal_id(request: RedRunRequest) -> str:
    payload: dict[str, Any] = {
        "match_id": request.match_id,
        "sandbox_id": request.sandbox_id,
        "scenario_id": request.scenario.scenario_id,
        "scenario_version": request.scenario.version,
        "profile_ref": request.agent_profile_ref,
    }
    digest = sha256(repr(sorted(payload.items())).encode()).hexdigest()
    return f"attackprop_{digest[:32]}"
