#!/usr/bin/env bash
#MISE description="Run locally with reload"
set -euo pipefail
uv run --locked uvicorn server.main:app --reload --port 3000
