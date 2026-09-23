# syntax=docker/dockerfile:1.7
# One image for every service (API, UI, Dagster webserver/daemon, MLflow). The deep-learning
# extra (PyTorch) is left out to keep the image small; N-HiTS runs outside the container.
FROM python:3.13-slim AS runtime

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

# LightGBM needs the OpenMP runtime; curl is for container health checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev \
        --extra ml --extra pipeline --extra serve --extra ui --extra monitor

COPY src ./src
COPY transform ./transform
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra ml --extra pipeline --extra serve --extra ui --extra monitor \
    && cd transform && /app/.venv/bin/dbt parse --profiles-dir . --quiet

ENV PATH=/app/.venv/bin:$PATH \
    GRIDCAST_BASE_DIR=/app \
    DAGSTER_HOME=/app/.dagster

RUN useradd --create-home --uid 1000 gridcast \
    && mkdir -p /app/data /app/reports /app/.dagster \
    && chown -R gridcast:gridcast /app
USER gridcast

EXPOSE 8000 8501 3000 5000
CMD ["gridcast", "serve", "--host", "0.0.0.0"]
