#!/bin/bash
# ERR Downloader Deployment Script
# Updates homelab server with latest code and config

set -e

HOMELAB="valme@homelab.local"
SSH_KEY="$HOME/.ssh/id_homelab"
APP_DIR="/opt/err_downloader"

echo "Deploying ERR Downloader to homelab..."
echo ""

# 1. Reset local changes and pull
echo "Pulling latest code from GitHub..."
ssh -i "$SSH_KEY" "$HOMELAB" "cd $APP_DIR && git reset --hard HEAD && git clean -fd && git pull origin main"
echo "Code updated"
echo ""

# 2. Copy config
echo "Copying config to homelab..."
scp -i "$SSH_KEY" config.homelab.yaml "$HOMELAB:$APP_DIR/config.yaml"
echo "Config updated"
echo ""

# 3. Update dependencies if needed
echo "Checking dependencies..."
ssh -i "$SSH_KEY" "$HOMELAB" "cd $APP_DIR && source venv/bin/activate && pip install -r requirements.txt --upgrade --quiet"
echo "Dependencies checked"
echo ""

echo "Deployment complete!"
echo ""
echo "To view logs:"
echo "  ssh $HOMELAB 'tail -f $APP_DIR/logs/downloader.log'"
