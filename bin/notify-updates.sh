#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="${KATALYST_REPOSITORY:-Envy-7z/katalyst}"
DATA_HOME="${KATALYST_DATA_HOME:-$HOME/.local/share/katalyst}"
CURRENT_VERSION="$(cat "$DATA_HOME/VERSION" 2>/dev/null || echo 0.1.0)"
LATEST_VERSION="$(curl -fsSL "https://api.github.com/repos/${REPOSITORY}/releases/latest" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tag_name", "").lstrip("v"))' 2>/dev/null || true)"

if [[ -n "$LATEST_VERSION" ]]; then
  NEWER="$(python3 -c "
def parse(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.split('-')[0].split('+')[0].split('.'))
print('true' if parse('$LATEST_VERSION') > parse('$CURRENT_VERSION') else 'false')
" 2>/dev/null || echo "false")"

  if [[ "$NEWER" == "true" ]]; then
    osascript -e "display notification \"Katalyst ${LATEST_VERSION} is available. Run katalyst-update.\" with title \"Katalyst Update\"" 2>/dev/null || true
  fi
fi
