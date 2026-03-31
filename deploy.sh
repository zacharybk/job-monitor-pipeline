#!/bin/bash
# Deploy job monitor pipeline to a fresh DigitalOcean droplet.
# Usage: bash deploy.sh
#
# After initial deploy, the droplet auto-updates from GitHub on every cron run.
# To pick up new sources or code changes: just push to main. No re-deploy needed.
#
# Pre-requisites:
#   1. Create Ubuntu 24.04 droplet ($6/mo Basic, 1 vCPU 1GB) in DO console
#   2. Update SERVER below with the droplet's IP
#   3. Ensure .env exists locally with SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY

SERVER="root@45.55.68.231"
REMOTE_DIR="/opt/job_monitor"
REPO="https://github.com/zacharybk/job-monitor-pipeline.git"

echo "=== Installing system dependencies ==="
ssh $SERVER "
  apt-get update -qq &&
  apt-get install -y python3 python3-pip python3-venv git -qq
"

echo "=== Cloning repo ==="
ssh $SERVER "
  if [ -d $REMOTE_DIR/.git ]; then
    cd $REMOTE_DIR && git pull
  else
    git clone $REPO $REMOTE_DIR
  fi
"

echo "=== Copying .env (secrets, not in git) ==="
scp .env $SERVER:$REMOTE_DIR/

echo "=== Installing Python dependencies ==="
ssh $SERVER "
  cd $REMOTE_DIR &&
  python3 -m venv .venv &&
  source .venv/bin/activate &&
  pip install -q -r requirements.txt &&
  playwright install chromium &&
  playwright install-deps chromium
"

echo "=== Setting up cron (10am + 4pm EST = 14:00 + 20:00 UTC) ==="
ssh $SERVER "
  crontab -l 2>/dev/null | grep -v '$REMOTE_DIR' | crontab - &&
  (crontab -l 2>/dev/null; echo '0 14 * * * cd $REMOTE_DIR && git pull -q && source .venv/bin/activate && python3 -m pipeline.run >> $REMOTE_DIR/pipeline.log 2>&1') | crontab - &&
  (crontab -l 2>/dev/null; echo '0 20 * * * cd $REMOTE_DIR && git pull -q && source .venv/bin/activate && python3 -m pipeline.run >> $REMOTE_DIR/pipeline.log 2>&1') | crontab -
  echo 'Cron jobs installed:' && crontab -l
"

echo ""
echo "=== Done! ==="
echo "The droplet now pulls from GitHub before every run."
echo "Push changes to main and they'll be live on the next cron cycle."
echo ""
echo "=== Run manually to test: ==="
echo "ssh $SERVER 'cd $REMOTE_DIR && git pull && source .venv/bin/activate && python3 -m pipeline.run'"
echo ""
echo "=== Tail logs: ==="
echo "ssh $SERVER 'tail -f $REMOTE_DIR/pipeline.log'"
