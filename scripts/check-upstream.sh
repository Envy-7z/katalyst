#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

echo "=== Checking Zed Upstream Updates ==="
echo "Fetching upstream main..."
git fetch upstream main

BEHIND=$(git rev-list --count HEAD..FETCH_HEAD)
AHEAD=$(git rev-list --count FETCH_HEAD..HEAD)

echo "Local branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Commits ahead of upstream: $AHEAD (our custom patches)"
echo "Commits behind upstream:  $BEHIND"

if [ "$BEHIND" -eq 0 ]; then
    echo "Up to date with upstream/main! No new updates from Zed developers."
else
    echo ""
    git log HEAD..FETCH_HEAD --oneline -n 10

    AGENT_COMMITS=$(git log HEAD..FETCH_HEAD --oneline crates/agent_ui crates/acp crates/acp_thread crates/agent 2>/dev/null || true)
    if [ -n "$AGENT_COMMITS" ]; then
        echo ""
        echo "=== WARNING: Upstream changes touch Agent UI / ACP crates ==="
        echo "$AGENT_COMMITS"
        echo "=============================================================="
    else
        echo ""
        echo "No recent upstream changes in agent_ui / acp modules."
    fi

    echo ""
    echo "To pull upstream changes and rebuild custom Zed, run:"
    echo "  bash $REPO_DIR/scripts/sync-and-rebuild.sh"
fi
