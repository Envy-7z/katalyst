#!/usr/bin/env bash
set -euo pipefail

echo "Rolling back to official Zed.app..."
if [ -d "/Applications/Zed.official-backup.app" ]; then
    pkill -x zed || true
    rm -rf "/Applications/Zed.app"
    cp -R "/Applications/Zed.official-backup.app" "/Applications/Zed.app"
    echo "Rollback complete: /Applications/Zed.app restored from official backup."
else
    echo "Error: /Applications/Zed.official-backup.app not found!"
    exit 1
fi
