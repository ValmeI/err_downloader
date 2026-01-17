#!/bin/bash
LOCKFILE="/tmp/err_downloader.lock"
APP_DIR="/opt/err_downloader"

# Check if already running
if [ -e "$LOCKFILE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Downloader already running, skipping"
    exit 0
fi

# Create lock file and cleanup on exit
touch "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Go to app directory
cd "$APP_DIR" || exit 1

# Activate venv and run (logging handled by Python)
source venv/bin/activate
python main.py
