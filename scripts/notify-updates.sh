#!/usr/bin/env bash
# Check OMP + Zed upstream; macOS-notify only when updates exist (or --test to preview).
set -euo pipefail

export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
REPO_DIR="$HOME/zed-custom"

NEED_OMP=0
NEED_ZED=0
MSG_PARTS=()

if [[ "${1:-}" == "--test" || "${1:-}" == "-t" ]]; then
  MSG="Zed custom behind upstream by 2 commit(s); OMP: New version available: 18.2.0"
  echo "[TEST] $MSG"
  osascript -e "display notification \"$MSG\" with title \"Zed / OMP Update Available\" subtitle \"Run update-all.sh to update\" sound name \"Glass\"" >/dev/null
  exit 0
fi

OMP_OUT="$(omp update --check 2>&1 || true)"
if echo "$OMP_OUT" | grep -q "New version available"; then
  NEED_OMP=1
  OMP_LINE="$(echo "$OMP_OUT" | grep -E "Current version:|New version available:" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g')"
  MSG_PARTS+=("OMP: ${OMP_LINE}")
fi

cd "$REPO_DIR"
git fetch upstream main >/dev/null 2>&1
BEHIND="$(git rev-list --count HEAD..upstream/main)"
if [[ "$BEHIND" -gt 0 ]]; then
  NEED_ZED=1
  MSG_PARTS+=("Zed custom behind upstream by ${BEHIND} commit(s)")
fi

if [[ "$NEED_OMP" -eq 0 && "$NEED_ZED" -eq 0 ]]; then
  exit 0
fi

MSG="$(IFS='; '; echo "${MSG_PARTS[*]}")"
echo "$MSG"
osascript -e "display notification \"$MSG\" with title \"Zed / OMP Update Available\" subtitle \"Run update-all.sh to update\" sound name \"Glass\"" >/dev/null
