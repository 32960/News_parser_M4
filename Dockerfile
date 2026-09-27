FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY . /app
