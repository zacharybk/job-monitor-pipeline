#!/bin/bash
# Morning applying agent — run manually anytime, or via launchd.
# Usage: bash run_morning_agent.sh [DRY_RUN]
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/Users/zach/.local/bin:$PATH"   # ensure `claude` is found under launchd
set -a; [ -f .env ] && . ./.env; set +a

# The morning agent authenticates via the Claude subscription (claude.ai login), not
# an API key. .env's ANTHROPIC_API_KEY is for the droplet scorer and is invalid here;
# leaving it set makes `claude -p` try that key and fail (this broke every launchd run).
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN

LOG="agent/morning_agent.log"
MODE="${1:-}"
echo "=== $(date '+%F %T') start (${MODE:-full}) ===" >> "$LOG"

PROMPT="$(cat agent/PROMPT.md)"
[ "$MODE" = "DRY_RUN" ] && PROMPT="DRY_RUN. $PROMPT"

TOOLS="Bash,Read,Write,WebSearch,WebFetch,Skill"
TOOLS="$TOOLS,mcp__lorikeet-cx-jobs__search_jobs,mcp__lorikeet-cx-jobs__get_job"
TOOLS="$TOOLS,mcp__lorikeet-cx-jobs__get_featured_jobs,mcp__lorikeet-cx-jobs__get_stats"

if claude -p "$PROMPT" --allowedTools "$TOOLS" >> "$LOG" 2>&1; then
  echo "=== $(date '+%F %T') ok ===" >> "$LOG"
  [ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "${HEALTHCHECK_URL}" >/dev/null 2>&1 || true
else
  echo "=== $(date '+%F %T') FAILED ===" >> "$LOG"
  [ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "${HEALTHCHECK_URL}/fail" >/dev/null 2>&1 || true
  exit 1
fi
