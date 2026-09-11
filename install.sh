#!/usr/bin/env bash
set -euo pipefail

KATALYST_VERSION="${KATALYST_VERSION:-0.2.0}"
KATALYST_REPOSITORY="${KATALYST_REPOSITORY:-Envy-7z/katalyst}"
KATALYST_DATA_HOME="${KATALYST_DATA_HOME:-$HOME/.local/share/katalyst}"
KATALYST_STATE_HOME="${KATALYST_STATE_HOME:-$HOME/.katalyst}"
KATALYST_APPLICATIONS_HOME="${KATALYST_APPLICATIONS_HOME:-/Applications}"
DRY_RUN=0
for argument in "$@"; do
  [[ "$argument" == "--dry-run" || "$argument" == "-n" ]] && DRY_RUN=1
done

case "${KATALYST_ARCH:-$(uname -m)}" in
  arm64|aarch64) RELEASE_ARCH="arm64" ;;
  x86_64|amd64) RELEASE_ARCH="x86_64" ;;
  *) echo "Unsupported macOS architecture: ${KATALYST_ARCH:-$(uname -m)}" >&2; exit 1 ;;
esac
APP_ASSET="Katalyst-v${KATALYST_VERSION}-macOS-${RELEASE_ARCH}.zip"
RUNTIME_ASSET="katalyst-runtime-v${KATALYST_VERSION}.tar.gz"
RELEASE_BASE="${KATALYST_RELEASE_BASE:-https://github.com/${KATALYST_REPOSITORY}/releases/download/v${KATALYST_VERSION}}"

echo "================================================="
echo "  ⚡ KATALYST ${KATALYST_VERSION}: OMP-first development"
echo "================================================="
echo "App asset:     ${APP_ASSET}"
echo "Runtime home:  ${KATALYST_DATA_HOME}"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] download ${RELEASE_BASE}/${APP_ASSET}"
  echo "[dry-run] verify SHA256SUMS and install ${KATALYST_APPLICATIONS_HOME}/Katalyst.app"
  echo "[dry-run] install ${RUNTIME_ASSET} into ${KATALYST_DATA_HOME}"
  echo "[dry-run] install OMP, Cursor/Codex sync helper, config, skills, and LaunchAgents"
  exit 0
fi

[[ "$(uname -s)" == "Darwin" ]] || { echo "Katalyst v0.2.0 currently supports macOS only." >&2; exit 1; }
for command in curl ditto python3 shasum tar; do
  command -v "$command" >/dev/null || { echo "Missing required command: $command" >&2; exit 1; }
done
if ! command -v omp >/dev/null 2>&1; then
  command -v brew >/dev/null || { echo "Homebrew is required to install OMP: https://brew.sh" >&2; exit 1; }
  brew install can1357/tap/omp
fi

TEMP_DIR="$(mktemp -d)"
INSTALL_COMPLETE=0
APP_ACTIVATED=0
DATA_ACTIVATED=0
APP_PREVIOUS_EXISTED=0
DATA_PREVIOUS_EXISTED=0
STATE_MIGRATED=0
LEGACY_SOURCE_BACKUP=""
USER_BACKUP_MANIFEST="$TEMP_DIR/user-backup-manifest"
SYNC_AGENT_WAS_LOADED=0
UPDATE_AGENT_WAS_LOADED=0
if [[ "${KATALYST_SKIP_LAUNCHCTL:-0}" != "1" ]]; then
  launchctl print "gui/$(id -u)/dev.katalyst.session-sync" >/dev/null 2>&1 && SYNC_AGENT_WAS_LOADED=1
  launchctl print "gui/$(id -u)/dev.katalyst.update-check" >/dev/null 2>&1 && UPDATE_AGENT_WAS_LOADED=1
fi
touch "$USER_BACKUP_MANIFEST"
backup_user_path() {
  local path="$1"
  local name="$2"
  if [[ -L "$path" ]]; then
    printf 'symlink|%s|%s|%s\n' "$name" "$path" "$(readlink "$path")" >> "$USER_BACKUP_MANIFEST"
  elif [[ -f "$path" ]]; then
    mkdir -p "$TEMP_DIR/user-backup/$(dirname "$name")"
    cp -p "$path" "$TEMP_DIR/user-backup/$name"
    printf 'file|%s|%s|\n' "$name" "$path" >> "$USER_BACKUP_MANIFEST"
  elif [[ -d "$path" ]]; then
    mkdir -p "$TEMP_DIR/user-backup/$(dirname "$name")"
    ditto "$path" "$TEMP_DIR/user-backup/$name"
    printf 'dir|%s|%s|\n' "$name" "$path" >> "$USER_BACKUP_MANIFEST"
  else
    printf 'absent|%s|%s|\n' "$name" "$path" >> "$USER_BACKUP_MANIFEST"
  fi
}
restore_user_paths() {
  local kind name path target
  while IFS='|' read -r kind name path target; do
    [[ -n "$path" ]] || continue
    rm -rf "$path"
    case "$kind" in
      symlink) mkdir -p "$(dirname "$path")"; ln -s "$target" "$path" ;;
      file) mkdir -p "$(dirname "$path")"; cp -p "$TEMP_DIR/user-backup/$name" "$path" ;;
      dir) mkdir -p "$(dirname "$path")"; ditto "$TEMP_DIR/user-backup/$name" "$path" ;;
    esac
  done < "$USER_BACKUP_MANIFEST"
}
cleanup() {
  status=$?
  if [[ "$INSTALL_COMPLETE" -ne 1 ]]; then
    if [[ "$APP_PREVIOUS_EXISTED" -eq 1 && -d "$KATALYST_APPLICATIONS_HOME/Katalyst.app.previous" ]]; then
      rm -rf "$KATALYST_APPLICATIONS_HOME/Katalyst.app"
      mv "$KATALYST_APPLICATIONS_HOME/Katalyst.app.previous" "$KATALYST_APPLICATIONS_HOME/Katalyst.app"
    elif [[ "$APP_ACTIVATED" -eq 1 ]]; then
      rm -rf "$KATALYST_APPLICATIONS_HOME/Katalyst.app"
    fi
    if [[ "$DATA_PREVIOUS_EXISTED" -eq 1 && -d "$KATALYST_DATA_HOME.previous" ]]; then
      rm -rf "$KATALYST_DATA_HOME"
      mv "$KATALYST_DATA_HOME.previous" "$KATALYST_DATA_HOME"
    elif [[ "$DATA_ACTIVATED" -eq 1 ]]; then
      rm -rf "$KATALYST_DATA_HOME"
    fi
    if [[ "$STATE_MIGRATED" -eq 1 && -d "$LEGACY_SOURCE_BACKUP" ]]; then
      rm -rf "$KATALYST_STATE_HOME"
      mv "$LEGACY_SOURCE_BACKUP" "$KATALYST_STATE_HOME"
    fi
    if [[ "${KATALYST_SKIP_LAUNCHCTL:-0}" != "1" ]]; then
      launchctl bootout "gui/$(id -u)/dev.katalyst.session-sync" 2>/dev/null || true
      launchctl bootout "gui/$(id -u)/dev.katalyst.update-check" 2>/dev/null || true
    fi
    restore_user_paths
    if [[ "${KATALYST_SKIP_LAUNCHCTL:-0}" != "1" ]]; then
      [[ "$SYNC_AGENT_WAS_LOADED" -eq 1 ]] && launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/dev.katalyst.session-sync.plist" 2>/dev/null || true
      [[ "$UPDATE_AGENT_WAS_LOADED" -eq 1 ]] && launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/dev.katalyst.update-check.plist" 2>/dev/null || true
    fi
  fi
  rm -rf "$TEMP_DIR"
  exit "$status"
}
trap cleanup EXIT

backup_user_path "$HOME/.local/bin/katalyst-session-sync" local-bin/session-sync
backup_user_path "$HOME/.local/bin/katalyst_session_sync.py" local-bin/session-sync-module
backup_user_path "$HOME/.local/bin/katalyst-update" local-bin/update
backup_user_path "$HOME/.local/bin/katalyst-notify" local-bin/notify
backup_user_path "$HOME/.config/zed/settings.json" config/zed-settings
backup_user_path "$HOME/.config/zed/keymap.json" config/zed-keymap
backup_user_path "$HOME/.omp/agent/config.yml" config/omp-config
backup_user_path "$HOME/.omp/agent/mcp.json" config/omp-mcp
backup_user_path "$HOME/.omp/agent/hooks/pre/plan-auto-open.ts" config/omp-hook
backup_user_path "$HOME/.omp/agent/skills" config/omp-skills
backup_user_path "$KATALYST_STATE_HOME/skills" state/skills
backup_user_path "$KATALYST_STATE_HOME/imports" state/imports
backup_user_path "$HOME/Library/LaunchAgents/dev.katalyst.session-sync.plist" launch/session-sync
backup_user_path "$HOME/Library/LaunchAgents/dev.katalyst.update-check.plist" launch/update-check

mkdir -p "$TEMP_DIR/config-snapshot"
snapshot_config() {
  local source="$1"
  local name="$2"
  if [[ -e "$source" || -L "$source" ]]; then
    cp -L "$source" "$TEMP_DIR/config-snapshot/$name" 2>/dev/null || true
  fi
}
snapshot_config "$HOME/.config/zed/settings.json" zed-settings.json
snapshot_config "$HOME/.config/zed/keymap.json" zed-keymap.json
snapshot_config "$HOME/.omp/agent/config.yml" omp-config.yml
snapshot_config "$HOME/.omp/agent/mcp.json" omp-mcp.json

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/lib/katalyst_session_sync.py" && -f "$SCRIPT_DIR/config/zed/settings.json" ]]; then
  RUNTIME_SOURCE="$SCRIPT_DIR"
else
  curl -fL "${RELEASE_BASE}/${RUNTIME_ASSET}" -o "$TEMP_DIR/${RUNTIME_ASSET}"
fi

curl -fL "${RELEASE_BASE}/SHA256SUMS" -o "$TEMP_DIR/SHA256SUMS"
curl -fL "${RELEASE_BASE}/${APP_ASSET}" -o "$TEMP_DIR/${APP_ASSET}"
(
  cd "$TEMP_DIR"
  for asset in "$APP_ASSET"; do
    [[ -n "$asset" ]] || continue
    expected="$(awk -v asset="$asset" '$2 == asset { print $1 }' SHA256SUMS)"
    [[ -n "$expected" ]] || { echo "No checksum published for ${asset}" >&2; exit 1; }
    actual="$(shasum -a 256 "$asset" | awk '{ print $1 }')"
    [[ "$actual" == "$expected" ]] || { echo "Checksum mismatch for ${asset}" >&2; exit 1; }
  done
)

if [[ -z "${RUNTIME_SOURCE:-}" ]]; then
  (
    cd "$TEMP_DIR"
    expected="$(awk -v asset="$RUNTIME_ASSET" '$2 == asset { print $1 }' SHA256SUMS)"
    [[ -n "$expected" ]] || { echo "No checksum published for ${RUNTIME_ASSET}" >&2; exit 1; }
    actual="$(shasum -a 256 "$RUNTIME_ASSET" | awk '{ print $1 }')"
    [[ "$actual" == "$expected" ]] || { echo "Checksum mismatch for ${RUNTIME_ASSET}" >&2; exit 1; }
  )
  mkdir -p "$TEMP_DIR/runtime"
  tar -xzf "$TEMP_DIR/${RUNTIME_ASSET}" -C "$TEMP_DIR/runtime"
  RUNTIME_SOURCE="$TEMP_DIR/runtime"
fi

mkdir -p "$TEMP_DIR/app"
ditto -x -k "$TEMP_DIR/${APP_ASSET}" "$TEMP_DIR/app"
[[ -d "$TEMP_DIR/app/Katalyst.app" ]] || { echo "Release does not contain Katalyst.app" >&2; exit 1; }
mkdir -p "$KATALYST_APPLICATIONS_HOME"
rm -rf "$KATALYST_APPLICATIONS_HOME/Katalyst.app.new"
ditto "$TEMP_DIR/app/Katalyst.app" "$KATALYST_APPLICATIONS_HOME/Katalyst.app.new"
if [[ -d "$KATALYST_APPLICATIONS_HOME/Katalyst.app" ]]; then
  rm -rf "$KATALYST_APPLICATIONS_HOME/Katalyst.app.previous"
  mv "$KATALYST_APPLICATIONS_HOME/Katalyst.app" "$KATALYST_APPLICATIONS_HOME/Katalyst.app.previous"
  APP_PREVIOUS_EXISTED=1
fi
mv "$KATALYST_APPLICATIONS_HOME/Katalyst.app.new" "$KATALYST_APPLICATIONS_HOME/Katalyst.app"
APP_ACTIVATED=1

rm -rf "$KATALYST_DATA_HOME.new"
mkdir -p "$KATALYST_DATA_HOME.new"
for directory in bin lib config skills assets; do
  [[ -d "$RUNTIME_SOURCE/$directory" ]] && ditto "$RUNTIME_SOURCE/$directory" "$KATALYST_DATA_HOME.new/$directory"
done
rm -rf "$KATALYST_DATA_HOME.previous"
if [[ -d "$KATALYST_DATA_HOME" ]]; then
  mv "$KATALYST_DATA_HOME" "$KATALYST_DATA_HOME.previous"
  DATA_PREVIOUS_EXISTED=1
fi
mv "$KATALYST_DATA_HOME.new" "$KATALYST_DATA_HOME"
DATA_ACTIVATED=1
printf '%s\n' "$KATALYST_VERSION" > "$KATALYST_DATA_HOME/VERSION"

if [[ -d "$KATALYST_STATE_HOME/.git" ]]; then
  LEGACY_SOURCE_BACKUP="$HOME/.local/share/katalyst-v0.1-source-$(date +%Y%m%d-%H%M%S)"
  mv "$KATALYST_STATE_HOME" "$LEGACY_SOURCE_BACKUP"
  STATE_MIGRATED=1
  echo "Preserved the v0.1 source checkout at $LEGACY_SOURCE_BACKUP"
  [[ "${KATALYST_TEST_FAIL_AFTER_STATE_MIGRATION:-0}" == "1" ]] && exit 99
fi

mkdir -p "$HOME/.local/bin" "$HOME/.config/zed" "$HOME/.omp/agent/hooks/pre" \
  "$KATALYST_STATE_HOME/imports" "$KATALYST_STATE_HOME/skills" "$HOME/Library/LaunchAgents"
install -m 755 "$KATALYST_DATA_HOME/bin/katalyst-session-sync" "$HOME/.local/bin/katalyst-session-sync"
install -m 644 "$KATALYST_DATA_HOME/lib/katalyst_session_sync.py" "$HOME/.local/bin/katalyst_session_sync.py"
install -m 755 "$KATALYST_DATA_HOME/bin/katalyst-update" "$HOME/.local/bin/katalyst-update"
install -m 755 "$KATALYST_DATA_HOME/bin/notify-updates.sh" "$HOME/.local/bin/katalyst-notify"

SETTINGS_CURRENT="$HOME/.config/zed/settings.json"
[[ -f "$TEMP_DIR/config-snapshot/zed-settings.json" ]] && SETTINGS_CURRENT="$TEMP_DIR/config-snapshot/zed-settings.json"
python3 - "$KATALYST_DATA_HOME/config/zed/settings.json" "$SETTINGS_CURRENT" "$HOME/.config/zed/settings.json" <<'PY'
import json, sys
from pathlib import Path
source, current_path, destination = map(Path, sys.argv[1:])
defaults = json.loads(source.read_text())
if current_path.exists():
    current = json.loads(current_path.read_text())
else:
    current = {}
if destination.is_symlink() or destination.exists():
    destination.unlink()
destination.parent.mkdir(parents=True, exist_ok=True)
current.setdefault("agent", {}).setdefault("dock", "left")
current.setdefault("agent_servers", {})["omp"] = defaults["agent_servers"]["omp"]
destination.write_text(json.dumps(current, indent=2) + "\n")
PY

materialize_config() {
  local source="$1"
  local destination="$2"
  local snapshot="${3:-}"
  if [[ -L "$destination" ]]; then unlink "$destination"; fi
  if [[ ! -e "$destination" && -n "$snapshot" && -f "$snapshot" ]]; then
    cp "$snapshot" "$destination"
  elif [[ ! -e "$destination" ]]; then
    cp "$source" "$destination"
  fi
}
materialize_config "$KATALYST_DATA_HOME/config/zed/keymap.json" "$HOME/.config/zed/keymap.json" "$TEMP_DIR/config-snapshot/zed-keymap.json"
materialize_config "$KATALYST_DATA_HOME/config/omp/config.yml" "$HOME/.omp/agent/config.yml" "$TEMP_DIR/config-snapshot/omp-config.yml"
materialize_config "$KATALYST_DATA_HOME/config/omp/mcp.json.example" "$HOME/.omp/agent/mcp.json" "$TEMP_DIR/config-snapshot/omp-mcp.json"
if [[ -f "$KATALYST_DATA_HOME/config/omp/hooks/pre/plan-auto-open.ts" ]]; then
  cp "$KATALYST_DATA_HOME/config/omp/hooks/pre/plan-auto-open.ts" "$HOME/.omp/agent/hooks/pre/plan-auto-open.ts"
fi
rm -rf "$KATALYST_STATE_HOME/skills.new"
ditto "$KATALYST_DATA_HOME/skills" "$KATALYST_STATE_HOME/skills.new"
rm -rf "$KATALYST_STATE_HOME/skills"
mv "$KATALYST_STATE_HOME/skills.new" "$KATALYST_STATE_HOME/skills"
if [[ -d "$HOME/.omp/agent/skills" && ! -L "$HOME/.omp/agent/skills" ]]; then
  for skill in "$HOME/.omp/agent/skills"/*; do
    [[ -e "$skill" ]] && ditto "$skill" "$KATALYST_STATE_HOME/skills/$(basename "$skill")"
  done
  mv "$HOME/.omp/agent/skills" "$HOME/.omp/agent/skills.pre-katalyst-$(date +%Y%m%d-%H%M%S)"
fi
ln -sfn "$KATALYST_STATE_HOME/skills" "$HOME/.omp/agent/skills"

cat > "$HOME/Library/LaunchAgents/dev.katalyst.session-sync.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>dev.katalyst.session-sync</string>
  <key>ProgramArguments</key><array>
    <string>$HOME/.local/bin/katalyst-session-sync</string>
    <string>sync</string><string>--sources</string><string>cursor,codex</string><string>--all</string><string>--automatic</string>
  </array>
  <key>WatchPaths</key><array>
    <string>$HOME/.cursor/projects</string><string>$HOME/.codex/sessions</string><string>$HOME/.codex/session_index.jsonl</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
PLIST
if [[ "${KATALYST_SKIP_LAUNCHCTL:-0}" != "1" ]]; then
  launchctl bootout "gui/$(id -u)/dev.katalyst.session-sync" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/dev.katalyst.session-sync.plist"
fi

cat > "$HOME/Library/LaunchAgents/dev.katalyst.update-check.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>dev.katalyst.update-check</string>
  <key>ProgramArguments</key><array><string>$HOME/.local/bin/katalyst-notify</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
</dict></plist>
PLIST
if [[ "${KATALYST_SKIP_LAUNCHCTL:-0}" != "1" ]]; then
  launchctl bootout "gui/$(id -u)/dev.katalyst.update-check" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/dev.katalyst.update-check.plist"
fi
"$HOME/.local/bin/katalyst-session-sync" sync --sources cursor,codex --all
[[ "${KATALYST_TEST_FAIL_AFTER_USER_MUTATIONS:-0}" == "1" ]] && exit 98

INSTALL_COMPLETE=1
rm -rf "$KATALYST_APPLICATIONS_HOME/Katalyst.app.previous" "$KATALYST_DATA_HOME.previous"

echo "Katalyst ${KATALYST_VERSION} installed. Open ${KATALYST_APPLICATIONS_HOME}/Katalyst.app."
