# Pinned by digest; keep versions in sync with .mise/config.toml (enforced in CI)
ARG PYTHON_IMAGE=python:3.14.8-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

FROM ${PYTHON_IMAGE} AS final
RUN useradd --system --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv ./.venv
# Copy only what the app needs at runtime
COPY server ./server
COPY problems ./problems
COPY public ./public
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
# One worker only: rooms live in memory, and uvicorn would otherwise honour WEB_CONCURRENCY
CMD ["sh", "-c", "exec uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
