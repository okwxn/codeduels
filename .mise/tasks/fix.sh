#!/usr/bin/env bash
#MISE description="Fix linting and formatting issues"
ruff check . --fix && ruff format .
