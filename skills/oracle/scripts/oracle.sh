#!/usr/bin/env bash
set -euo pipefail

# Prefer an installed CLI, but keep the skill usable on machines where Oracle
# is only available through npm.
if command -v oracle >/dev/null 2>&1; then
  exec oracle "$@"
fi

exec npx -y @steipete/oracle "$@"
