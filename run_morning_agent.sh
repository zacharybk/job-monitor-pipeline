#!/bin/bash
# Morning applying agent — run manually anytime, or via launchd.
# Usage: bash run_morning_agent.sh [DRY_RUN]
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/Users/zach/.local/bin:$PATH"   # ensure `claude` is found under launchd
set -a; [ -f .env ] && . ./.env; set +a

LOG="agent/morning_agent.log"
MODE="${1:-}"
echo "=== $(date '+%F %T') start (${MODE:-full}) ===" >> "$LOG"

PROMPT="$(cat agent/PROMPT.md)"
[ "$MODE" = "DRY_RUN" ] && PROMPT="DRY_RUN. $PROMPT"

if claude -p "$PROMPT" --allowedTools "Bash,Read,Write,WebSearch,Skill" >> "$LOG" 2>&1; then
  echo "=== $(date '+%F %T') ok ===" >> "$LOG"
  [ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "${HEALTHCHECK_URL}" >/dev/null 2>&1 || true
else
  echo "=== $(date '+%F %T') FAILED ===" >> "$LOG"
  [ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "${HEALTHCHECK_URL}/fail" >/dev/null 2>&1 || true
  exit 1
fi
