#!/usr/bin/env bash
#MISE description="Fix linting and formatting issues"
set -euo pipefail
uv run --locked ruff check . --fix && uv run --locked ruff format .
