#!/usr/bin/env bash
# ==============================================================================
# katalyst-export: Sync local custom commits, run privacy audit, and prepare push
# ==============================================================================
set -euo pipefail

KATALYST_DIR="$HOME/katalyst"
ZED_DIR="$HOME/zed-custom"

echo "=== 1. Exporting Zed Patches ==="
if [[ -d "$ZED_DIR" ]]; then
  cd "$ZED_DIR"
  rm -f "$KATALYST_DIR/patches/"*.patch
  git format-patch upstream/main..HEAD -o "$KATALYST_DIR/patches/" >/dev/null
  PATCH_COUNT="$(ls -1 "$KATALYST_DIR/patches/"*.patch | wc -l | tr -d ' ')"
  echo "   ✓ Exported $PATCH_COUNT patches to $KATALYST_DIR/patches/"
fi

echo "=== 2. Running Privacy Audit ==="
cd "$KATALYST_DIR"
bash "$KATALYST_DIR/scripts/audit-privacy.sh"

echo ""
echo "=== 3. Git Status in Katalyst ==="
git status --short

if git diff-index --quiet HEAD -- 2>/dev/null && [[ -z "$(git status --porcelain)" ]]; then
  echo "No changes to commit in Katalyst repo."
  exit 0
fi

if [[ -t 0 ]]; then
  read -r -p "Commit and push updates to Katalyst GitHub? [y/N] " ans
  if [[ "$ans" =~ ^[yY]$ ]]; then
    read -r -p "Commit message: " msg
    msg="${msg:-update Katalyst suite}"
    git add .
    git commit -m "$msg"
    if git remote | grep -q "^origin$"; then
      echo "Pushing to GitHub origin..."
      git push origin main
      echo "✓ Pushed successfully!"
    else
      echo "Tip: Add your GitHub remote with:"
      echo "  git remote add origin https://github.com/Envy-7z/katalyst.git"
      echo "  git push -u origin main"
    fi
  fi
fi
