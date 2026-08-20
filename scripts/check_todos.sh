#!/usr/bin/env bash
set -euo pipefail

matches="$(grep -R "TODO(student)" -n src tests \
  --include="*.py" \
  --exclude-dir="__pycache__" \
  --exclude-dir="*.egg-info" || true)"

if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches"
  exit 1
fi

printf 'No core TODO(student) markers found.\n'
