# 1. Base Stage: Install dependencies (Cached)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base
WORKDIR /app

# Copy dependency definitions first to leverage Docker layer caching
# If pyproject.toml doesn't change, this layer is cached
COPY pyproject.toml uv.lock /app/

# Install dependencies into .venv 
# (without installing the project -aka my code- itself yet)
RUN uv sync --frozen --no-install-project

# 2. Orchestrator Stage
FROM base AS orchestrator
# Copy the rest of the source code
COPY . /app
# Install the project and any missing orchestrator dependencies
RUN uv sync --frozen --group orchestrator

# 3. Streamlit Stage
FROM base AS streamlit
COPY . /app
RUN uv sync --frozen --group streamlit
