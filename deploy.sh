#!/bin/bash
# Deploy job monitor pipeline to a fresh DigitalOcean droplet.
# Usage: bash deploy.sh
#
# Pre-requisites:
#   1. Create Ubuntu 24.04 droplet ($6/mo Basic, 1 vCPU 1GB) in DO console
#   2. Update SERVER below with the droplet's IP
#   3. Ensure .env exists locally with SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY

SERVER="root@YOUR_DROPLET_IP"   # <-- update this
REMOTE_DIR="/opt/job_monitor"

echo "=== Creating remote directory structure ==="
ssh $SERVER "mkdir -p $REMOTE_DIR/pipeline/scrapers $REMOTE_DIR/tests"

echo "=== Copying pipeline files ==="
scp -r pipeline/ $SERVER:$REMOTE_DIR/
scp requirements.txt .env $SERVER:$REMOTE_DIR/

echo "=== Installing system dependencies ==="
ssh $SERVER "
  apt-get update -qq &&
  apt-get install -y python3 python3-pip python3-venv -qq
"

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
  (crontab -l 2>/dev/null; echo '0 14 * * * cd $REMOTE_DIR && source .venv/bin/activate && python3 -m pipeline.run >> $REMOTE_DIR/pipeline.log 2>&1') | crontab - &&
  (crontab -l 2>/dev/null; echo '0 20 * * * cd $REMOTE_DIR && source .venv/bin/activate && python3 -m pipeline.run >> $REMOTE_DIR/pipeline.log 2>&1') | crontab -
  echo 'Cron jobs installed:' && crontab -l
"

echo ""
echo "=== Done! Run manually to test: ==="
echo "ssh $SERVER 'cd $REMOTE_DIR && source .venv/bin/activate && python3 -m pipeline.run'"
echo ""
echo "=== Tail logs: ==="
echo "ssh $SERVER 'tail -f $REMOTE_DIR/pipeline.log'"
