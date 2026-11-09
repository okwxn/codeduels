#!/usr/bin/env bash
#MISE description="Run the test suite"
set -euo pipefail
uv run --locked pytest -q