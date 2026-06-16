from collections.abc import Mapping

POLICY_VERSION = "identity-policy-v1"

_ACTION_SCOPE_MAP: Mapping[str, str] = {
    "scenario.publish": "admin:scenarios",
    "scenario.read": "scenarios:read",
    "scenarios.read": "scenarios:read",
    "match.create": "matches:write",
    "match.read": "matches:read",
    "findings.read": "findings:read",
    "findings.write": "findings:write",
    "identity.admin": "admin:identity",
}


def required_scope_for_action(action: str) -> str:
    return _ACTION_SCOPE_MAP.get(action, action.replace(".", ":"))
