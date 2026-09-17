#!/usr/bin/env bash
# Install Katalyst Git hooks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_DIR/.git/hooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "Error: .git/hooks directory not found at $HOOKS_DIR" >&2
  exit 1
fi

cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Git pre-commit privacy & secret guard hook installed successfully."
