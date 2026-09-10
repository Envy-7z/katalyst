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

# 2b. OMP-Cost Installation (AI Token Spend & FinOps Telemetry)
echo "2b. Checking omp-cost (Token Telemetry CLI)..."
if ! command -v omp-cost >/dev/null 2>&1; then
  echo "   Installing omp-cost via installer..."
  run_cmd bash -c 'curl -fsSL https://raw.githubusercontent.com/faridlamaul/omp-cost/main/install.sh | bash' 2>/dev/null || true
else
  echo "   ✓ omp-cost is installed ($(omp-cost --version 2>/dev/null || echo 'active'))."
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
  # Bundle id must change or App Switcher/Dock keep caching the app as Zed.
  plutil -replace CFBundleIdentifier -string "dev.katalyst.Katalyst" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
  # Keep CFBundleExecutable=zed and URL scheme "zed" for binary/deep-link compatibility.
  /usr/libexec/PlistBuddy -c "Set :CFBundleDocumentTypes:1:CFBundleTypeName Katalyst Text Document" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleURLTypes:0:CFBundleURLName Katalyst" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
  for key in \
    NSAppleEventsUsageDescription \
    NSCalendarsUsageDescription \
    NSCameraUsageDescription \
    NSContactsUsageDescription \
    NSLocationUsageDescription \
    NSLocationAlwaysUsageDescription \
    NSLocationWhenInUseUsageDescription \
    NSMicrophoneUsageDescription \
    NSRemindersUsageDescription \
    NSBluetoothAlwaysUsageDescription \
    NSSpeechRecognitionUsageDescription \
    NSSystemAdministrationUsageDescription
  do
    val="$(/usr/libexec/PlistBuddy -c "Print :$key" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true)"
    if [[ -n "$val" && "$val" == *Zed* ]]; then
      new_val="${val//Zed/Katalyst}"
      /usr/libexec/PlistBuddy -c "Set :$key $new_val" /Applications/Katalyst.app/Contents/Info.plist 2>/dev/null || true
    fi
  done
  if [[ -f "$SCRIPT_DIR/assets/Katalyst.icns" ]]; then
    run_cmd cp "$SCRIPT_DIR/assets/Katalyst.icns" "/Applications/Katalyst.app/Contents/Resources/Katalyst.icns" 2>/dev/null || true
    run_cmd cp "$SCRIPT_DIR/assets/Katalyst.icns" "/Applications/Katalyst.app/Contents/Resources/Zed.icns" 2>/dev/null || true
  fi
  run_cmd codesign --force --sign - /Applications/Katalyst.app 2>/dev/null || true
  run_cmd touch /Applications/Katalyst.app 2>/dev/null || true
  LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
  if [[ -x "$LSREG" ]]; then
    run_cmd "$LSREG" -f /Applications/Katalyst.app 2>/dev/null || true
  fi
  run_cmd killall Dock 2>/dev/null || true
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

# 5b. Plan auto-open hook (hard path — do not rely on prompt rules alone)
echo "5b. Installing plan auto-open OMP hook..."
run_cmd mkdir -p "$HOME/.omp/agent/hooks/pre"
if [[ -f "$SCRIPT_DIR/config/omp/hooks/pre/plan-auto-open.ts" ]]; then
  run_cmd cp "$SCRIPT_DIR/config/omp/hooks/pre/plan-auto-open.ts" "$HOME/.omp/agent/hooks/pre/plan-auto-open.ts"
  if [[ -f "$HOME/.omp/agent/config.yml" ]] && ! grep -Fq "plan-auto-open.ts" "$HOME/.omp/agent/config.yml"; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] register plan-auto-open.ts in config.yml extensions"
    else
      python3 - <<'PY'
from pathlib import Path
p = Path.home() / ".omp/agent/config.yml"
text = p.read_text()
line = "  - ~/.omp/agent/hooks/pre/plan-auto-open.ts\n"
if "plan-auto-open.ts" in text:
    print("   ✓ plan-auto-open already registered")
elif "extensions:\n" in text:
    p.write_text(text.replace("extensions:\n", "extensions:\n" + line, 1))
    print("   ✓ Registered plan-auto-open.ts in config.yml extensions")
else:
    p.write_text(text.rstrip() + "\nextensions:\n" + line)
    print("   ✓ Added extensions block with plan-auto-open.ts")
PY
    fi
  else
    echo "   ✓ plan-auto-open.ts present"
  fi
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
echo "  4. Check AI Token Spend:     omp-cost"
echo "  5. Check for updates:        katalyst-update"
echo ""
