#!/usr/bin/env bash
#MISE description="Build the Docker image"
set -euo pipefail
docker build -t codeduels .
