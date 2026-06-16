from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthTokenResponse:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int
    subject_id: str
    tenant_id: str
    scopes: tuple[str, ...]
