#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="${KATALYST_REPOSITORY:-Envy-7z/katalyst}"
DATA_HOME="${KATALYST_DATA_HOME:-$HOME/.local/share/katalyst}"
CURRENT_VERSION="$(cat "$DATA_HOME/VERSION" 2>/dev/null || echo 0.1.0)"
LATEST_VERSION="$(curl -fsSL "https://api.github.com/repos/${REPOSITORY}/releases/latest" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))' 2>/dev/null || true)"

if [[ -n "$LATEST_VERSION" && "$CURRENT_VERSION" != "$LATEST_VERSION" ]]; then
  osascript -e "display notification \"Katalyst ${LATEST_VERSION} is available. Run katalyst-update.\" with title \"Katalyst Update\"" 2>/dev/null || true
fi
