#!/usr/bin/env bash
#MISE description="Fix linting and formatting issues"
uv run ruff check . --fix && uv run ruff format .
