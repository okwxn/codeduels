#!/usr/bin/env bash
#MISE description="Lint/type check with ruff and ty"
set -euo pipefail
echo "Running ruff..."
ruff check .
ruff format --check .
echo "Running ty..."
ty check .
