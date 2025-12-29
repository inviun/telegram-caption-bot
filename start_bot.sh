#!/usr/bin/env bash
set -euo pipefail
ENV_FILE=${1:-.env}
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi
python bot.py
