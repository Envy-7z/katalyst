#!/usr/bin/env bash
# ==============================================================================
# Katalyst Zero-Leak Privacy & Security Audit
# Scans all repository files to ensure zero secrets or private paths are committed.
# ==============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "=== Katalyst Zero-Leak Privacy Audit ==="
ERRORS=0

# 1. Hardcoded /Users/ or /home/ local paths
echo -n "Checking for hardcoded local user paths (/Users/ or /home/)... "
LOCAL_PATHS="$(grep -rEn --exclude-dir=".git" --exclude-dir="__pycache__" --exclude="audit-privacy.sh" "(/(Users|home)/[a-zA-Z0-9_-]+)" . 2>/dev/null | grep -v "/api/users/" || true)"
if [[ -n "$LOCAL_PATHS" ]]; then
  echo "FAILED!"
  echo "$LOCAL_PATHS"
  ERRORS=$((ERRORS + 1))
else
  echo "OK (clean)"
fi

# 2. Private Auth Tokens and Secret Keys
echo -n "Checking for secret API keys, auth tokens, and personal profile identifiers... "
TOKEN_PATTERNS="(ghp_[a-zA-Z0-9]{20,}|glpat-[a-zA-Z0-9_-]{20,}|sk-ant-[a-zA-Z0-9_-]{20,}|sk-[a-zA-Z0-9_-]{20,}|AIzaSy[a-zA-Z0-9_-]{33}|xoxb-[a-zA-Z0-9-]+|BEGIN[A-Z ]*PRIVATE KEY|wisnuandrian[0-9a-z._-]*@|geniebook\.com)"
MATCHES_TOKENS="$(grep -rEn --exclude-dir=".git" --exclude-dir="__pycache__" --exclude="audit-privacy.sh" "$TOKEN_PATTERNS" . 2>/dev/null || true)"
if [[ -n "$MATCHES_TOKENS" ]]; then
  echo "FAILED!"
  echo "$MATCHES_TOKENS"
  ERRORS=$((ERRORS + 1))
else
  echo "OK (clean)"
fi

# 3. Custom Private Keywords (optional via env var)
if [[ -n "${KATALYST_AUDIT_KEYWORDS:-}" ]]; then
  echo -n "Checking custom private keywords ($KATALYST_AUDIT_KEYWORDS)... "
  MATCHES_CUSTOM="$(grep -rEni --exclude-dir=".git" --exclude-dir="__pycache__" --exclude="audit-privacy.sh" "$KATALYST_AUDIT_KEYWORDS" . 2>/dev/null || true)"
  if [[ -n "$MATCHES_CUSTOM" ]]; then
    echo "FAILED!"
    echo "$MATCHES_CUSTOM"
    ERRORS=$((ERRORS + 1))
  else
    echo "OK (clean)"
  fi
fi

echo ""
if [[ "$ERRORS" -gt 0 ]]; then
  echo "❌ Privacy Audit FAILED with $ERRORS issue(s). Do NOT push."
  exit 1
else
  echo "✅ Privacy Audit PASSED: 100% clean. Safe for public distribution."
  exit 0
fi
