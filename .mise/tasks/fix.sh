#!/usr/bin/env bash
#MISE description="Fix linting and formatting issues"
set -euo pipefail
uv run ruff check . --fix && uv run ruff format .
