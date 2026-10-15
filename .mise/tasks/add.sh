#!/usr/bin/env bash
#MISE description="Clipboard -> new problem folder(s) -> generate tests"
set -euo pipefail
command -v pbpaste >/dev/null || { echo "mise r add needs pbpaste (macOS)" >&2; exit 1; }
pbpaste | uv run python tools/new_problem.py && uv run python tools/gen_tests.py
