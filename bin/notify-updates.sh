#!/usr/bin/env bash
# Katalyst daily update notification for macOS.
set -euo pipefail

export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
NEED_OMP=0
NEED_ZED=0
MSG_PARTS=()

if [[ "${1:-}" == "--test" || "${1:-}" == "-t" ]]; then
  MSG="Katalyst behind upstream by 2 commit(s); OMP: New version available"
  osascript -e "display notification \"$MSG\" with title \"Katalyst Update Available\" subtitle \"Run katalyst-update to update\" sound name \"Glass\"" >/dev/null
  exit 0
fi

if command -v omp >/dev/null 2>&1; then
  OMP_OUT="$(omp update --check 2>&1 || true)"
  if echo "$OMP_OUT" | grep -q "New version available"; then
    NEED_OMP=1
    MSG_PARTS+=("OMP: New version available")
  fi
fi

if [[ -d "$HOME/zed-custom" ]]; then
  cd "$HOME/zed-custom"
  git fetch upstream main >/dev/null 2>&1 || true
  BEHIND="$(git rev-list --count HEAD..upstream/main 2>/dev/null || echo 0)"
  if [[ "$BEHIND" -gt 0 ]]; then
    NEED_ZED=1
    MSG_PARTS+=("Katalyst behind upstream by ${BEHIND} commit(s)")
  fi
fi

if [[ "$NEED_OMP" -eq 0 && "$NEED_ZED" -eq 0 ]]; then
  exit 0
fi

MSG="$(IFS='; '; echo "${MSG_PARTS[*]}")"
echo "$MSG"
osascript -e "display notification \"$MSG\" with title \"Katalyst Update Available\" subtitle \"Run katalyst-update to update\" sound name \"Glass\"" >/dev/null
