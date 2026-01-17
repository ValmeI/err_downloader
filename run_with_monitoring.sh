#!/bin/bash
#
# ERR Downloader - Wrapper script for homelab cron jobs
#
# This script:
# 1. Activates the virtual environment
# 2. Runs main.py (which reads config.yaml)
# 3. Propagates the exit code
#
# NOTE: This script is for homelab production use only.
# For local development, just run: python main.py

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found (looked for 'venv' and '.venv')"
    exit 1
fi

# Run the main script and capture exit code
python main.py
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Exit with the same code as main.py
exit $EXIT_CODE
