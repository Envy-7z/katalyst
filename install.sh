#!/usr/bin/env bash
# ==============================================================================
# Katalyst ⚡ Universal Installer
# Autonomous Agentic Development Suite powered by Zed Editor + OMP (ACP)
# ==============================================================================
set -euo pipefail

KATALYST_HOME="${KATALYST_HOME:-$HOME/.katalyst}"
DRY_RUN=0

for arg in "$@"; do
  if [[ "$arg" == "--dry-run" || "$arg" == "-n" ]]; then
    DRY_RUN=1
  fi
done

echo "================================================="
echo "  ⚡ KATALYST: Agentic Development Environment"
echo "================================================="
echo ""

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[DRY-RUN MODE ENABLED - No changes will be made]"
  echo ""
fi

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

# 0. Detect if executed via curl | bash (piped)
if [[ -z "${BASH_SOURCE[0]:-}" || "${BASH_SOURCE[0]:-}" == "bash" || "${BASH_SOURCE[0]:-}" == "/bin/bash" || "${BASH_SOURCE[0]:-}" == "/dev/fd/"* ]]; then
  SCRIPT_DIR="$KATALYST_HOME"
  if [[ ! -d "$KATALYST_HOME" ]]; then
    echo "0. Downloading Katalyst into $KATALYST_HOME..."
    run_cmd git clone https://github.com/Envy-7z/katalyst.git "$KATALYST_HOME"
  else
    echo "0. Updating existing Katalyst in $KATALYST_HOME..."
    run_cmd git -C "$KATALYST_HOME" pull --ff-only 2>/dev/null || true
  fi
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# 1. Prerequisite Checks
echo "1. Checking prerequisites..."
if ! command -v brew >/dev/null 2>&1; then
  echo "Error: Homebrew is required on macOS. Install from https://brew.sh first."
  exit 1
fi
echo "   ✓ Homebrew found."

# 2. OMP Installation
echo "2. Checking OMP (Agent Engine)..."
if ! command -v omp >/dev/null 2>&1; then
  echo "   Installing OMP via Homebrew..."
  run_cmd brew install can1357/tap/omp
else
  echo "   ✓ OMP is installed ($(omp --version 2>/dev/null || echo 'active'))."
fi

# 3. Editor Installation & Branding
echo "3. Checking Editor (Katalyst / Zed)..."
if [[ ! -d "/Applications/Katalyst.app" && ! -d "/Applications/Zed.app" ]]; then
  echo "   Installing Zed Editor via Homebrew..."
  run_cmd brew install --cask zed
fi

if [[ -d "/Applications/Zed.app" && ! -d "/Applications/Katalyst.app" ]]; then
  echo "   Promoting bundle to /Applications/Katalyst.app..."
  run_cmd mv "/Applications/Zed.app" "/Applications/Katalyst.app"
  run_cmd ln -sfn "/Applications/Katalyst.app" "/Applications/Zed.app"
fi

if [[ -d "/Applications/Katalyst.app" ]]; then
  plutil -replace CFBundleDisplayName -string "Katalyst" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
  plutil -replace CFBundleName -string "Katalyst" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
  plutil -replace CFBundleIconFile -string "Katalyst.icns" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
  if [[ -f "$SCRIPT_DIR/assets/Katalyst.icns" ]]; then
    run_cmd cp "$SCRIPT_DIR/assets/Katalyst.icns" "/Applications/Katalyst.app/Contents/Resources/Katalyst.icns" 2>/dev/null || true
    run_cmd cp "$SCRIPT_DIR/assets/Katalyst.icns" "/Applications/Katalyst.app/Contents/Resources/Zed.icns" 2>/dev/null || true
  fi
  run_cmd codesign --force --sign - /Applications/Katalyst.app 2>/dev/null || true
  run_cmd touch /Applications/Katalyst.app 2>/dev/null || true
  echo "   ✓ Katalyst.app is ready in /Applications/."
fi

# 4. Directory Structure
echo "4. Setting up configuration directories..."
run_cmd mkdir -p "$HOME/.config/zed"
run_cmd mkdir -p "$HOME/.omp/agent"
run_cmd mkdir -p "$HOME/.katalyst/skills"
run_cmd mkdir -p "$HOME/.katalyst/plans"
run_cmd mkdir -p "$HOME/.local/bin"

# 5. Linking Configurations
echo "5. Linking Katalyst configs..."

backup_and_link() {
  local src="$1"
  local dest="$2"
  if [[ -f "$dest" && ! -L "$dest" ]]; then
    echo "   Backing up existing $dest -> ${dest}.backup"
    run_cmd mv "$dest" "${dest}.backup"
  fi
  run_cmd ln -sfn "$src" "$dest"
  echo "   ✓ Linked $dest"
}

backup_and_link "$SCRIPT_DIR/config/zed/settings.json" "$HOME/.config/zed/settings.json"
backup_and_link "$SCRIPT_DIR/config/zed/keymap.json" "$HOME/.config/zed/keymap.json"
backup_and_link "$SCRIPT_DIR/config/omp/config.yml" "$HOME/.omp/agent/config.yml"

if [[ ! -f "$HOME/.omp/agent/mcp.json" ]]; then
  echo "   Creating starter $HOME/.omp/agent/mcp.json from template..."
  run_cmd cp "$SCRIPT_DIR/config/omp/mcp.json.example" "$HOME/.omp/agent/mcp.json"
fi

# 6. Installing Universal Engineering Skills
echo "6. Installing universal engineering skills to ~/.katalyst/skills/..."
for skill_dir in "$SCRIPT_DIR/skills"/*; do
  if [[ -d "$skill_dir" ]]; then
    skill_name="$(basename "$skill_dir")"
    run_cmd cp -R "$skill_dir" "$HOME/.katalyst/skills/$skill_name"
    echo "   ✓ Skill: $skill_name"
  fi
done

run_cmd ln -sfn "$HOME/.katalyst/skills" "$HOME/.omp/agent/skills"

# 7. Linking Binary Tools
echo "7. Linking Katalyst binaries into ~/.local/bin/..."
run_cmd ln -sfn "$SCRIPT_DIR/bin/katalyst-update" "$HOME/.local/bin/katalyst-update"
run_cmd ln -sfn "$SCRIPT_DIR/bin/notify-updates.sh" "$HOME/.local/bin/katalyst-notify"

# 8. Setup Daily LaunchAgent
echo "8. Configuring daily update checker..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.katalyst.update-check.plist"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] configure LaunchAgent at $PLIST_PATH"
else
  cat <<PLIST > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.katalyst.update-check</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/bash</string>
		<string>$HOME/.local/bin/katalyst-notify</string>
	</array>
	<key>StartCalendarInterval</key>
	<dict>
		<key>Hour</key>
		<integer>9</integer>
		<key>Minute</key>
		<integer>0</integer>
	</dict>
	<key>RunAtLoad</key>
	<true/>
</dict>
</plist>
PLIST
  launchctl bootout "gui/$(id -u)/com.katalyst.update-check" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
  echo "   ✓ LaunchAgent registered for daily 09:00 checks."
fi

echo ""
echo "================================================="
echo "  ✅ KATALYST INSTALLATION COMPLETE!"
echo "================================================="
echo ""
echo "To get started:"
echo "  1. Open Katalyst:            open -a Katalyst (or zed .)"
echo "  2. Open Agent Panel:         Cmd + Shift + A"
echo "  3. Open any *.plan.md file:  Review and click [ ▶ Build Locally ]"
echo "  4. Check for updates:        katalyst-update"
echo ""
