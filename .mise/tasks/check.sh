#!/usr/bin/env bash
#MISE description="Lint/type check with ruff and ty"
set -euo pipefail
echo "Running ruff..."
uv run --locked ruff check .
uv run --locked ruff format --check .
echo "Running ty..."
uv run --locked ty check .
