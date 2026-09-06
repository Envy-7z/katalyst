#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
export CARGO_INCREMENTAL=0
export RUSTFLAGS="-C debuginfo=0"

echo "=== Zed Custom: Sync Upstream & Rebuild ==="

# Check git status
if ! git diff-index --quiet HEAD --; then
    echo "Error: Working directory has uncommitted changes. Please commit or stash them first."
    exit 1
fi

echo "1. Fetching upstream main..."
git fetch upstream main

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

BEHIND=$(git rev-list --count HEAD..FETCH_HEAD)
if [ "$BEHIND" -eq 0 ]; then
    echo "Already up to date with upstream main (0 commits behind)."
else
    echo "2. Rebasing $CURRENT_BRANCH onto upstream main ($BEHIND new commits)..."
    if ! git rebase FETCH_HEAD; then
        echo ""
        echo "Rebase conflict detected!"
        echo "Aborting rebase to preserve branch state..."
        git rebase --abort
        echo "Rebase aborted cleanly. Please resolve conflicts manually in $REPO_DIR."
        exit 1
    fi
fi

echo "3. Verifying agent_ui compilation..."
cargo check -p agent_ui

echo "4. Building release binary..."
cargo build --release -p zed

echo "5. Installing into /Applications/Zed.app..."
if [ -d "/Applications/Zed.app" ]; then
    if [ ! -d "/Applications/Zed.official-backup.app" ]; then
        cp -R "/Applications/Zed.app" "/Applications/Zed.official-backup.app"
    fi
    cp "$REPO_DIR/target/release/zed" "/Applications/Zed.app/Contents/MacOS/zed"
    echo "Installed successfully to /Applications/Zed.app/Contents/MacOS/zed!"
fi

echo "=== Sync and rebuild complete! ==="
