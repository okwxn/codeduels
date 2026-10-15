#!/usr/bin/env bash
#MISE description="Lint/type check with ruff and ty"
set -euo pipefail
echo "Running ruff..."
uv run ruff check .
uv run ruff format --check .
echo "Running ty..."
uv run ty check .
