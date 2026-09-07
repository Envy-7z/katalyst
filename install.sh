#!/usr/bin/env bash
# ==============================================================================
# Katalyst ⚡ Universal Installer
# Autonomous Agentic Development Suite powered by Zed Editor + OMP (ACP)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
  DRY_RUN=1
  echo "[DRY-RUN MODE ENABLED - No changes will be made]"
fi

echo "================================================="
echo "  ⚡ KATALYST: Agentic Development Environment"
echo "================================================="
echo ""

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

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

# 3. Directory Structure
echo "3. Setting up configuration directories..."
run_cmd mkdir -p "$HOME/.config/zed"
run_cmd mkdir -p "$HOME/.omp/agent"
run_cmd mkdir -p "$HOME/.katalyst/skills"
run_cmd mkdir -p "$HOME/.katalyst/plans"
run_cmd mkdir -p "$HOME/.local/bin"

# 4. Linking Configurations
echo "4. Linking Katalyst configs..."

# Backup existing config if real file and not already pointing to katalyst
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

# 5. Installing Universal Engineering Skills
echo "5. Installing universal engineering skills to ~/.katalyst/skills/..."
for skill_dir in "$SCRIPT_DIR/skills"/*; do
  if [[ -d "$skill_dir" ]]; then
    skill_name="$(basename "$skill_dir")"
    run_cmd cp -R "$skill_dir" "$HOME/.katalyst/skills/$skill_name"
    echo "   ✓ Skill: $skill_name"
  fi
done
# Link skills into OMP agent runtime directory
run_cmd ln -sfn "$HOME/.katalyst/skills" "$HOME/.omp/agent/skills"

# 6. Linking Binary Tools
echo "6. Linking Katalyst binaries into ~/.local/bin/..."
run_cmd ln -sfn "$SCRIPT_DIR/bin/katalyst-update" "$HOME/.local/bin/katalyst-update"
run_cmd ln -sfn "$SCRIPT_DIR/bin/notify-updates.sh" "$HOME/.local/bin/katalyst-notify"

# 7. Setup Daily LaunchAgent
echo "7. Configuring daily update checker..."
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
echo "  1. Open Katalyst (or Zed):   open -a Katalyst (or zed .)"
echo "  2. Open Agent Panel:         Cmd + Shift + A"
echo "  3. Open any *.plan.md file:  Review and click [ ▶ Build Locally ]"
echo "  4. Check for updates:        katalyst-update"
echo ""
