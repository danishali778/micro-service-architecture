from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query

app = FastAPI(title="Local Scenario Service Stub")


@app.get("/internal/v1/scenarios")
async def list_scenarios(
    auth_mode: Annotated[str | None, Header(alias="X-Internal-Auth-Mode")] = None,
    tenant_id: Annotated[str | None, Header(alias="X-Internal-Tenant-ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    if auth_mode != "local" or not tenant_id:
        raise HTTPException(status_code=401, detail="local trusted context required")

    scenarios = [
        {
            "id": "scn_sql_injection_login",
            "latest_version": "1.0.0",
            "title": "SQL Injection Login Bypass",
            "summary": f"Tenant-visible training scenario for {tenant_id}.",
            "difficulty": "beginner",
            "category": "web-security",
            "tags": ["sql-injection", "authentication"],
            "estimated_duration_minutes": 30,
            "status": "published",
        },
        {
            "id": "scn_auth_boundary",
            "latest_version": "1.0.0",
            "title": "Authorization Boundary",
            "summary": "Practice detecting and fixing an authorization bypass.",
            "difficulty": "intermediate",
            "category": "web-security",
            "tags": ["authorization", "multi-tenant"],
            "estimated_duration_minutes": 45,
            "status": "published",
        },
    ]
    return {
        "items": scenarios[:limit],
        "next_cursor": cursor,
    }
