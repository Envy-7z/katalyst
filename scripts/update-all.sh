#!/usr/bin/env bash
# One-command OMP + Zed custom update.
# Non-interactive (no TTY): updates OMP + prints Zed delta, never rebuilds.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"

echo "=== OMP before ==="
omp --version

echo "=== Updating OMP ==="
omp update

echo "=== OMP after ==="
omp --version

echo ""
bash "$SCRIPT_DIR/check-upstream.sh"

cd "$REPO_DIR"
# check-upstream.sh already fetched; recompute from upstream/main for safety
git fetch upstream main >/dev/null 2>&1 || true
BEHIND="$(git rev-list --count HEAD..upstream/main)"

if [[ "$BEHIND" -eq 0 ]]; then
  echo "Zed already up to date with upstream/main."
  exit 0
fi

if [[ ! -t 0 ]]; then
  echo "Non-interactive shell: skipping Zed sync+rebuild ($BEHIND commits behind)."
  echo "Re-run in a terminal and confirm, or:"
  echo "  ZED_MIN_FREE_GB=8 bash $SCRIPT_DIR/sync-and-rebuild.sh"
  exit 0
fi

read -r -p "Sync+rebuild Zed now? [y/N] " ans
if [[ "$ans" =~ ^[yY]$ ]]; then
  ZED_MIN_FREE_GB="${ZED_MIN_FREE_GB:-8}" bash "$SCRIPT_DIR/sync-and-rebuild.sh"
else
  echo "Skipped Zed sync+rebuild."
fi
