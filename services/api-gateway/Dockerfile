FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /workspace
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
COPY pyproject.toml uv.lock .python-version ./
COPY services/api-gateway/pyproject.toml services/api-gateway/pyproject.toml
RUN uv sync --frozen --package api-gateway --no-dev --no-install-workspace

FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system gateway && useradd --system --gid gateway gateway
COPY --from=builder /opt/venv /opt/venv
COPY services/api-gateway/app /opt/service/app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/opt/service" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1"

WORKDIR /opt/service
USER gateway
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
