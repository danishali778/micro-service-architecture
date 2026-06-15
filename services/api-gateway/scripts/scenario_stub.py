from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query

app = FastAPI(title="Local Scenario Service Stub")


@app.get("/internal/scenarios")
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
            "scenario_id": "scenario-sql-injection",
            "name": "SQL Injection Basics",
            "description": f"Tenant-visible training scenario for {tenant_id}.",
            "version": 1,
        },
        {
            "scenario_id": "scenario-auth-bypass",
            "name": "Authorization Boundary",
            "description": "Practice detecting and fixing an authorization bypass.",
            "version": 1,
        },
    ]
    return {
        "items": scenarios[:limit],
        "next_cursor": cursor,
    }
