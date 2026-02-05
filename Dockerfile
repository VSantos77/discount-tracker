# Setting base image: Astral UV with Python 3.12 on Bookworm Slim (lightweight)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory and copy project files
WORKDIR /app
COPY . /app

# Install dependencies using uv
RUN uv sync --frozen
