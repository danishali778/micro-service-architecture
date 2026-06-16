FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /workspace
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
COPY pyproject.toml uv.lock .python-version ./
COPY services/identity-service/pyproject.toml services/identity-service/pyproject.toml
RUN uv sync --frozen --package identity-service --no-dev --no-install-workspace

FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system identity && useradd --system --gid identity identity
COPY --from=builder /opt/venv /opt/venv
COPY services/identity-service/app /opt/service/app
COPY services/identity-service/alembic.ini /opt/service/alembic.ini
COPY services/identity-service/scripts /opt/service/scripts

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/opt/service" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1"

WORKDIR /opt/service
USER identity
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
