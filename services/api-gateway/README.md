# API Gateway

The API gateway is the public FastAPI edge service. Milestone one implements
health checks and authenticated scenario listing.

## Setup

From the repository root:

```powershell
$env:UV_CACHE_DIR="$PWD\.uv-cache"
uv sync --all-packages --group dev --locked
```

## Run Locally

Start these commands in separate terminals:

```powershell
uv run uvicorn scripts.dev_oidc:app --app-dir services/api-gateway --port 9000
uv run uvicorn scripts.scenario_stub:app --app-dir services/api-gateway --port 9100
uv run uvicorn app.main:app --app-dir services/api-gateway --port 8000
```

Issue a local token and call the gateway:

```powershell
$token = uv run python services/api-gateway/scripts/issue_dev_token.py
Invoke-RestMethod -Headers @{ Authorization = "Bearer $token" } `
  -Uri "http://127.0.0.1:8000/api/v1/scenarios"
```

## Checks

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy services/api-gateway/app services/api-gateway/scripts
uv run pytest
uv run python services/api-gateway/scripts/validate_openapi.py
docker build -f services/api-gateway/Dockerfile .
```
