#!/usr/bin/env bash
#MISE description="Clipboard -> new problem folder(s) -> generate tests"
pbpaste | uv run python tools/new_problem.py && uv run python tools/gen_tests.py
