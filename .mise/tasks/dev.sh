#!/usr/bin/env bash
#MISE description="Run locally with reload"
uv run uvicorn main:app --reload --port 3000
