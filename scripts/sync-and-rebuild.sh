#!/usr/bin/env bash
# Sync upstream main (optional rebase) then OOM-safe rebuild/install.
# On 16GB Macs: never thinLTO release while Zed GUI is open.
# Default build profile is release-fast (lto=false). Override: ZED_BUILD_PROFILE=release
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PROFILE="${ZED_BUILD_PROFILE:-release-fast}"
JOBS="${ZED_BUILD_JOBS:-2}"
MIN_FREE_GB="${ZED_MIN_FREE_GB:-12}"

cd "$REPO_DIR"
export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
export CARGO_INCREMENTAL=0
export RUSTFLAGS="${RUSTFLAGS:--C debuginfo=0}"

if [[ "$PROFILE" == "release" ]]; then
  export CARGO_PROFILE_RELEASE_LTO=false
fi

echo "=== Zed Custom: Sync Upstream & OOM-safe Rebuild ==="

if pgrep -f '/Applications/Katalyst.app/Contents/MacOS/zed' >/dev/null 2>&1 \
  || pgrep -f '/Applications/Zed.app/Contents/MacOS/zed' >/dev/null 2>&1; then
  echo "Error: Katalyst is running. Quit Katalyst first (Cmd+Q), then re-run this script."
  exit 1
fi

FREE_GB="$(df -g "$HOME" | awk 'NR==2 {print $4}')"
if [[ -z "$FREE_GB" || "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
  echo "Error: free disk ${FREE_GB:-?}GB < ${MIN_FREE_GB}GB."
  exit 1
fi

if ! git diff-index --quiet HEAD --; then
  echo "Error: Working directory has uncommitted changes. Commit or stash first."
  exit 1
fi

echo "1. Fetching upstream main..."
git fetch upstream main

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Current branch: $CURRENT_BRANCH"

BEHIND="$(git rev-list --count HEAD..FETCH_HEAD)"
if [[ "$BEHIND" -eq 0 ]]; then
  echo "Already up to date with upstream main (0 commits behind)."
else
  echo "2. Rebasing $CURRENT_BRANCH onto upstream main ($BEHIND new commits)..."
  if ! git rebase FETCH_HEAD; then
    echo ""
    echo "Rebase conflict detected — aborting to preserve branch state."
    git rebase --abort
    echo "Rebase aborted. Resolve conflicts manually in $REPO_DIR."
    exit 1
  fi
fi

echo "3. Verifying agent_ui compilation..."
cargo check -p agent_ui -j "$JOBS"

echo "4. Clearing incremental caches..."
rm -rf target/release/incremental target/release-fast/incremental target/*/incremental 2>/dev/null || true

echo "5. Building with --profile $PROFILE -j $JOBS ..."
cargo build --profile "$PROFILE" -p zed -j "$JOBS"

SRC="$REPO_DIR/target/$PROFILE/zed"
APP_BUNDLE="/Applications/Katalyst.app"
if [[ ! -d "$APP_BUNDLE" && -d "/Applications/Zed.app" ]]; then
  APP_BUNDLE="/Applications/Zed.app"
fi
APP_BIN="$APP_BUNDLE/Contents/MacOS/zed"
echo "6. Installing into $APP_BUNDLE..."
if [[ -d "$APP_BUNDLE" ]]; then
  if [[ ! -d "/Applications/Zed.official-backup.app" && -d "/Applications/Zed.app" ]]; then
    cp -R "/Applications/Zed.app" "/Applications/Zed.official-backup.app"
  fi
  cp "$SRC" "$APP_BIN"
  # Preserve Katalyst branding (name, icon, App Switcher id)
  plutil -replace CFBundleDisplayName -string "Katalyst" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || true
  plutil -replace CFBundleName -string "Katalyst" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || true
  plutil -replace CFBundleIconFile -string "Katalyst.icns" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || true
  plutil -replace CFBundleIdentifier -string "dev.katalyst.Katalyst" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || true
  if [[ -f "$REPO_DIR/assets/Katalyst.icns" ]]; then
    cp "$REPO_DIR/assets/Katalyst.icns" "$APP_BUNDLE/Contents/Resources/Katalyst.icns" 2>/dev/null || true
    cp "$REPO_DIR/assets/Katalyst.icns" "$APP_BUNDLE/Contents/Resources/Zed.icns" 2>/dev/null || true
  fi
  echo "Re-signing $APP_BUNDLE (ad-hoc)..."
  codesign --force --deep --sign - "$APP_BUNDLE"
  ln -sfn "$APP_BUNDLE" "/Applications/Zed.app" 2>/dev/null || true
  echo "Installed and signed successfully to $APP_BIN"
else
  echo "Warning: $APP_BUNDLE missing; binary at $SRC"
fi

echo "=== Sync and rebuild complete! Do not reopen Katalyst until this finished. ==="
