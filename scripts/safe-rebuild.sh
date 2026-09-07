#!/usr/bin/env bash
# OOM-safe local rebuild + install for custom Zed on 16GB Macs.
# NEVER run cargo release thinLTO while the Zed GUI is open — that ballooned
# to ~50GB swap and Force Quit. Prefer release-fast (lto=false) + -j2.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
APP_BUNDLE="/Applications/Katalyst.app"
APP_BIN="$APP_BUNDLE/Contents/MacOS/zed"
JOBS="${ZED_BUILD_JOBS:-2}"
MIN_FREE_GB="${ZED_MIN_FREE_GB:-12}"
PROFILE="${ZED_BUILD_PROFILE:-release-fast}"
cd "$REPO_DIR"
export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
export CARGO_INCREMENTAL=0
export RUSTFLAGS="${RUSTFLAGS:--C debuginfo=0}"

if [[ "$PROFILE" == "release" ]]; then
  export CARGO_PROFILE_RELEASE_LTO=false
fi

echo "=== Zed Custom: safe-rebuild (profile=$PROFILE, -j$JOBS) ==="

if pgrep -f '/Applications/Katalyst.app/Contents/MacOS/zed' >/dev/null 2>&1 \
  || pgrep -f '/Applications/Zed.app/Contents/MacOS/zed' >/dev/null 2>&1; then
  echo "Error: Katalyst is running. Quit Katalyst first (Cmd+Q), then re-run:"
  echo "  bash $SCRIPT_DIR/safe-rebuild.sh"
  exit 1
fi

FREE_GB="$(df -g "$HOME" | awk 'NR==2 {print $4}')"
if [[ -z "$FREE_GB" || "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
  echo "Error: free disk ${FREE_GB:-?}GB < ${MIN_FREE_GB}GB. Free space or lower ZED_MIN_FREE_GB."
  exit 1
fi
echo "Disk free: ${FREE_GB}GB (ok)"

echo "Clearing incremental caches (keeping deps)..."
rm -rf target/release/incremental target/release-fast/incremental target/*/incremental 2>/dev/null || true

echo "Building zed with --profile $PROFILE -j $JOBS ..."
cargo build --profile "$PROFILE" -p zed -j "$JOBS"

PROFILE_DIR="$PROFILE"
SRC="$REPO_DIR/target/$PROFILE_DIR/zed"
if [[ ! -x "$SRC" ]]; then
  echo "Error: missing binary at $SRC"
  exit 1
fi

if [[ -d "$APP_BUNDLE" ]]; then
  echo "Installing $SRC -> $APP_BIN"
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
  echo "Installed and signed. Safe to reopen Katalyst now."
else
  echo "Warning: $APP_BUNDLE missing; binary at $SRC"
fi

echo "=== safe-rebuild complete ==="
