#!/usr/bin/env bash
# OOM-safe local rebuild + install for custom Zed on 16GB Macs.
# NEVER run cargo release thinLTO while the Zed GUI is open — that ballooned
# to ~50GB swap and Force Quit. Prefer release-fast (lto=false) + -j2.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
APP_BIN="/Applications/Zed.app/Contents/MacOS/zed"
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

echo "=== Zed Custom: safe-rebuild (profile=$PROFILE, -j$JOBS) ==="

if pgrep -f '/Applications/Zed.app/Contents/MacOS/zed' >/dev/null 2>&1; then
  echo "Error: Zed is running. Quit Zed first (Cmd+Q), then re-run:"
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

if [[ -d "/Applications/Zed.app" ]]; then
  if [[ ! -d "/Applications/Zed.official-backup.app" ]]; then
    echo "Backing up official app once -> /Applications/Zed.official-backup.app"
    cp -R "/Applications/Zed.app" "/Applications/Zed.official-backup.app"
  fi
  echo "Installing $SRC -> $APP_BIN"
  cp "$SRC" "$APP_BIN"
  # Preserve Katalyst branding (name and icon)
  plutil -replace CFBundleDisplayName -string "Katalyst" /Applications/Zed.app/Contents/Info.plist 2>/dev/null || true
  plutil -replace CFBundleName -string "Katalyst" /Applications/Zed.app/Contents/Info.plist 2>/dev/null || true
  plutil -replace CFBundleIconFile -string "Katalyst.icns" /Applications/Zed.app/Contents/Info.plist 2>/dev/null || true
  if [[ -f "$REPO_DIR/assets/Katalyst.icns" ]]; then
    cp "$REPO_DIR/assets/Katalyst.icns" /Applications/Zed.app/Contents/Resources/Katalyst.icns 2>/dev/null || true
    cp "$REPO_DIR/assets/Katalyst.icns" /Applications/Zed.app/Contents/Resources/Zed.icns 2>/dev/null || true
  fi
  echo "Re-signing /Applications/Zed.app (ad-hoc)..."
  codesign --force --deep --sign - /Applications/Zed.app
  echo "Installed and signed. Safe to reopen Zed now."
else
  echo "Warning: /Applications/Zed.app missing; binary at $SRC"
fi

echo "=== safe-rebuild complete ==="
