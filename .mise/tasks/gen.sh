#!/usr/bin/env bash
#MISE description="Build problems/*.json from problems_src/"
set -euo pipefail
uv run python tools/gen_tests.py
