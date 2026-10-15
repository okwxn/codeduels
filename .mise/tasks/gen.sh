#!/usr/bin/env bash
#MISE description="Build problems/*.json from problems_src/, removing tracked orphans (--check: fail if stale)"
set -euo pipefail
uv run --locked python tools/gen_tests.py "$@"
