#!/bin/bash
# ERR Downloader runtime script
# Deployed by deploy.sh

LOCKFILE="/tmp/err_downloader.lock"
APP_DIR="/opt/err_downloader"

# Check if already running (with stale lock detection)
if [ -e "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S'): Downloader already running (PID $OLD_PID), skipping"
        exit 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S'): Removing stale lock file (PID $OLD_PID no longer running)"
        rm -f "$LOCKFILE"
    fi
fi

# Create lock file with PID and cleanup on exit
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Go to app directory
cd "$APP_DIR" || exit 1

# Activate venv and run (logging handled by Python)
source venv/bin/activate
python main.py --discover --add # add new urls to config, in case it found new ones
python main.py # just run the downloader
