FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /workspace
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
COPY pyproject.toml uv.lock .python-version ./
COPY services/scenario-service/pyproject.toml services/scenario-service/pyproject.toml
RUN uv sync --frozen --package scenario-service --no-dev --no-install-workspace

FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system scenario && useradd --system --gid scenario scenario
COPY --from=builder /opt/venv /opt/venv
COPY services/scenario-service/app /opt/service/app
COPY services/scenario-service/alembic.ini /opt/service/alembic.ini
COPY services/scenario-service/scripts /opt/service/scripts

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/opt/service" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1"

WORKDIR /opt/service
USER scenario
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
