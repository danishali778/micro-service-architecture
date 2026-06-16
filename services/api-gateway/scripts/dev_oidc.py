import os
import time
from typing import Any
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ISSUER = os.getenv("DEV_SUPABASE_JWT_ISSUER", "http://127.0.0.1:9999/auth/v1").rstrip("/")
KEY_ID = "local-development-key"
AUDIENCE = "authenticated"
DEMO_EMAIL = os.getenv("DEV_USER_EMAIL", "learner@example.com")
DEMO_PASSWORD = os.getenv("DEV_USER_PASSWORD", "password")
DEMO_SUPABASE_USER_ID = os.getenv("DEV_SUPABASE_USER_ID", "supabase_user_demo")
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
PUBLIC_JWK: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(
    PRIVATE_KEY.public_key(), as_dict=True
)
PUBLIC_JWK.update({"kid": KEY_ID, "alg": "RS256", "use": "sig"})

app = FastAPI(title="Local OIDC Stub")


class PasswordTokenRequest(BaseModel):
    email: str = DEMO_EMAIL
    password: str = DEMO_PASSWORD


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str


@app.get("/auth/v1/.well-known/openid-configuration")
async def discovery() -> dict[str, Any]:
    return {
        "issuer": ISSUER,
        "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
        "id_token_signing_alg_values_supported": ["RS256"],
    }


@app.get("/auth/v1/.well-known/jwks.json")
async def jwks() -> dict[str, Any]:
    return {"keys": [PUBLIC_JWK]}


@app.post("/auth/v1/token")
async def issue_token(
    request: PasswordTokenRequest | RefreshTokenRequest,
    grant_type: str,
) -> dict[str, Any]:
    if grant_type == "password":
        if not isinstance(request, PasswordTokenRequest):
            raise HTTPException(status_code=400, detail="invalid_request")
        if request.email != DEMO_EMAIL or request.password != DEMO_PASSWORD:
            raise HTTPException(status_code=400, detail="invalid_grant")
    elif grant_type != "refresh_token":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    session_id = str(uuid4())
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": DEMO_SUPABASE_USER_ID,
            "session_id": session_id,
            "role": "authenticated",
            "iat": now,
            "exp": now + 3_600,
        },
        PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )
    return {
        "access_token": token,
        "refresh_token": "refresh-token",
        "token_type": "bearer",
        "expires_in": 3_600,
        "user": {"id": DEMO_SUPABASE_USER_ID, "email": DEMO_EMAIL},
    }


@app.post("/auth/v1/logout")
async def logout() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/v1/admin/users")
async def create_user(request: AdminCreateUserRequest) -> dict[str, str]:
    return {"id": DEMO_SUPABASE_USER_ID, "email": request.email}
