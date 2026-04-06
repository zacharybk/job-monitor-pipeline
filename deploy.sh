#!/bin/bash
# Deploy job monitor pipeline to a DigitalOcean droplet.
# Usage: bash deploy.sh
#
# One SSH authentication prompt. Everything else is automated:
#   - Clones/updates repo from GitHub
#   - Copies .env (secrets)
#   - Installs dependencies
#   - Applies Supabase schema (idempotent)
#   - Migrates local state to Supabase (idempotent)
#   - Sets up cron (auto-pulls from GitHub before every run)
#
# Pre-requisites:
#   1. Create Ubuntu 24.04 droplet ($6/mo Basic, 1 vCPU 1GB) in DO console
#   2. Update SERVER below with the droplet's IP
#   3. .env must contain SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, HEALTHCHECK_URL

set -e

SERVER="root@45.55.68.231"
REMOTE_DIR="/opt/job_monitor"
REPO="https://github.com/zacharybk/job-monitor-pipeline.git"

# ── Single SSH connection reused for all commands ─────────────────────────────
SOCKET="/tmp/deploy-job-monitor.sock"
SSH="ssh -o ControlMaster=auto -o ControlPath=$SOCKET -o ControlPersist=yes"
SCP="scp -o ControlMaster=auto -o ControlPath=$SOCKET"

cleanup() { ssh -o ControlPath=$SOCKET -O exit $SERVER 2>/dev/null; }
trap cleanup EXIT

echo "=== Connecting (one auth prompt) ==="
$SSH $SERVER "echo Connected"

echo "=== Installing system dependencies ==="
$SSH $SERVER "apt-get update -qq && apt-get install -y python3 python3-pip python3-venv git nginx -qq"

echo "=== Cloning / updating repo ==="
$SSH $SERVER "
  if [ -d $REMOTE_DIR/.git ]; then
    cd $REMOTE_DIR && git pull -q
  else
    rm -rf $REMOTE_DIR && git clone -q $REPO $REMOTE_DIR
  fi
"

echo "=== Copying .env and profile.md ==="
$SCP .env $SERVER:$REMOTE_DIR/
$SCP profile.md $SERVER:$REMOTE_DIR/

echo "=== Installing Python dependencies ==="
$SSH $SERVER "
  cd $REMOTE_DIR &&
  python3 -m venv .venv &&
  source .venv/bin/activate &&
  pip install -q -r requirements.txt &&
  playwright install chromium &&
  playwright install-deps chromium
"

echo "=== Deploying review UI ==="
$SCP review.html $SERVER:/var/www/html/review.html
$SSH $SERVER "systemctl enable nginx -q && systemctl start nginx -q || systemctl reload nginx -q"
echo "    Review UI: http://45.55.68.231/review.html"

echo "=== Migrating local state to Supabase (safe to re-run) ==="
$SSH $SERVER "
  cd $REMOTE_DIR &&
  source .venv/bin/activate &&
  python3 migrate_state.py
"

echo "=== Setting up cron (10am + 4pm EST = 14:00 + 20:00 UTC) ==="
$SSH $SERVER "
  crontab -l 2>/dev/null | grep -v '$REMOTE_DIR' | crontab - ;
  (crontab -l 2>/dev/null; echo '0 14 * * * cd $REMOTE_DIR && git pull -q && source .venv/bin/activate && python3 -m pipeline.run >> $REMOTE_DIR/pipeline.log 2>&1') | crontab - &&
  (crontab -l 2>/dev/null; echo '0 20 * * * cd $REMOTE_DIR && git pull -q && source .venv/bin/activate && python3 -m pipeline.run >> $REMOTE_DIR/pipeline.log 2>&1') | crontab -
  echo 'Cron:' && crontab -l
"

echo ""
echo "=== Done ==="
echo "Push changes to main — the droplet picks them up on the next cron run."
echo ""
echo "Test run:  ssh $SERVER 'cd $REMOTE_DIR && git pull && source .venv/bin/activate && python3 -m pipeline.run'"
echo "Tail logs: ssh $SERVER 'tail -f $REMOTE_DIR/pipeline.log'"
