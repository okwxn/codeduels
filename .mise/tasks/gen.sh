#!/usr/bin/env bash
#MISE description="Build problems/*.json from problems_src/"
uv run python tools/gen_tests.py
