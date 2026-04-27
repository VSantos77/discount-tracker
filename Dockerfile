# --- STAGE 1: Shared Base (Standard Python Slim) ---
FROM python:3.12-slim-bookworm AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
# Ensure the .venv is in PATH

# --- STAGE 2: Scrapy Builder ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS scrapy-builder
# UV cache is stored separately to avoid including it in the final image
# and link mode is set to copy for better compatibility
ENV UV_LINK_MODE=copy UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /app
COPY pyproject.toml uv.lock ./
# Install ONLY scrapy dependencies
RUN uv sync --frozen --no-install-project --group scrapy --no-dev

# --- STAGE 3: dbt Builder ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dbt-builder
ENV UV_LINK_MODE=copy UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /app
COPY pyproject.toml uv.lock ./
# Install ONLY dbt dependencies
RUN uv sync --frozen --no-install-project --group dbt --no-dev

# ---------------------------------------------------------
# FINAL TARGET: SCRAPY (The Runner)
# ---------------------------------------------------------
FROM base AS scrapy
# Copy the specific scrapy venv
# Only copy the finished .venv for lighter image size
COPY --from=scrapy-builder /app/.venv /app/.venv                        
# Copy scrapy code only
COPY discount_tracker_scrapy/ ./discount_tracker_scrapy/
COPY scrapy.cfg .
ENTRYPOINT ["scrapy"]

# ---------------------------------------------------------
# FINAL TARGET: DBT (The Runner)
# ---------------------------------------------------------
FROM base AS dbt
# Copy the specific dbt venv
COPY --from=dbt-builder /app/.venv /app/.venv
# Copy dbt code only
COPY discount_tracker_dbt/ ./discount_tracker_dbt/
ENTRYPOINT ["dbt"]