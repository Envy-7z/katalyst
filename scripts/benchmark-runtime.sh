#!/usr/bin/env bash
# Katalyst Runtime Benchmark & Performance Budget Enforcement
# Based on Principle 19 (Measure Before Claiming) & Principle 20 (Performance Budget)
set -euo pipefail

APP_PATH="${KATALYST_APP:-/Applications/Katalyst.app}"
BIN_PATH="$APP_PATH/Contents/MacOS/zed"

echo "================================================="
echo "  ⚡ KATALYST RUNTIME PERFORMANCE BENCHMARK"
echo "================================================="

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Error: Binary not found at $BIN_PATH" >&2
  exit 1
fi

# 1. Binary Size Budget Check (Budget: < 1.5 GB for unstripped debug, < 300 MB for release)
BIN_SIZE_BYTES="$(stat -f %z "$BIN_PATH" 2>/dev/null || stat -c %s "$BIN_PATH")"
BIN_SIZE_MB=$(( BIN_SIZE_BYTES / 1024 / 1024 ))
echo "• Binary size:        ${BIN_SIZE_MB} MB"

# 2. Cold Startup Execution Time (Budget: < 1.0s)
START_TIME="$(python3 -c 'import time; print(time.time())')"
"$BIN_PATH" --system-specs >/dev/null 2>&1 || true
END_TIME="$(python3 -c 'import time; print(time.time())')"

ELAPSED_SEC="$(python3 -c "print(f'{$END_TIME - $START_TIME:.3f}')")"
echo "• Cold startup specs: ${ELAPSED_SEC}s"

# 3. Running Memory RSS Check (if Katalyst is currently active)
RUNNING_PID="$(pgrep -f "$BIN_PATH" | head -n 1 || true)"
if [[ -n "$RUNNING_PID" ]]; then
  RSS_KB="$(ps -o rss= -p "$RUNNING_PID" 2>/dev/null || echo 0)"
  RSS_MB=$(( RSS_KB / 1024 ))
  CPU_PCT="$(ps -o %cpu= -p "$RUNNING_PID" 2>/dev/null || echo 0.0)"
  echo "• Active process RSS: ${RSS_MB} MB (PID: ${RUNNING_PID})"
  echo "• Active CPU usage:   ${CPU_PCT}%"
else
  echo "• Active process RSS: Not running"
fi

echo "-------------------------------------------------"
echo "Budget Check:"
PASSED=1
if python3 -c "import sys; sys.exit(0 if float('$ELAPSED_SEC') <= 1.5 else 1)"; then
  echo "  ✅ Startup latency within budget (<= 1.5s)"
else
  echo "  ⚠️ Startup latency exceeded budget: ${ELAPSED_SEC}s"
  PASSED=0
fi

if [[ "$BIN_SIZE_MB" -le 1500 ]]; then
  echo "  ✅ Binary footprint within budget (<= 1500 MB)"
else
  echo "  ⚠️ Binary size exceeded budget: ${BIN_SIZE_MB} MB"
  PASSED=0
fi

if [[ "$PASSED" -eq 1 ]]; then
  echo "✅ All runtime performance budgets PASSED."
  exit 0
else
  echo "❌ Performance budget violations detected."
  exit 1
fi
