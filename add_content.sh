#!/bin/bash
# Validate a lasteekraan.err.ee URL locally, then append it directly on the homelab's
# config.yaml. Bypasses deploy.sh's config sync (see deploy.sh for why).
set -euo pipefail

REMOTE_HOST="${HOMELAB_HOST:-homelab.local}"
SSH_KEY="${HOMELAB_SSH_KEY:-$HOME/.ssh/id_homelab}"
REMOTE_CONFIG="/opt/err_downloader/config.yaml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

banner() {
    gum style --border rounded --padding "0 2" --margin "1 0" \
        --border-foreground 212 --bold "📺 ERR Downloader — Add Content"
}

ok()   { gum style --foreground 82 "✔ $*"; }
fail() { gum style --foreground 196 "✖ $*"; }
step() { gum style --bold --foreground 212 "▶ $*"; }

usage() { echo "Usage: $(basename "$0") [lasteekraan.err.ee URL] [tv|movie]"; exit 1; }
[[ $# -le 2 ]] || usage

banner

URL="${1:-}"
[[ -z "$URL" ]] && URL="$(gum input --placeholder "https://lasteekraan.err.ee/XXXXXXX/nimi" --header "ERR URL")"
[[ "$URL" == https://lasteekraan.err.ee/* ]] || { fail "Not a lasteekraan.err.ee URL: $URL"; exit 1; }

KIND="${2:-}"
[[ -z "$KIND" ]] && KIND="$(gum choose --header "Add to which list?" tv movie)"

case "$KIND" in
    tv) LIST_KEY="tv_shows" ;;
    movie) LIST_KEY="movies" ;;
    *) usage ;;
esac

step "Validating URL against ERR API..."
if ! (
    cd "$SCRIPT_DIR"
    source .venv/bin/activate
    python3 -c "
import sys
from err_api import extract_video_id, fetch_video_api_data, _has_playable_content

video_id = extract_video_id('$URL')
if video_id is None:
    sys.exit('could not extract video ID')
data = fetch_video_api_data(video_id)
if data is None:
    sys.exit('content not found on ERR (404/removed)')
if not _has_playable_content(data):
    sys.exit('no playable media or season list')
"
); then
    fail "URL failed validation, not adding"
    exit 1
fi
ok "URL is valid and playable"

if ssh -i "$SSH_KEY" "$REMOTE_HOST" "grep -qxF -- '- $URL' $REMOTE_CONFIG"; then
    ok "Already present: $URL"
    exit 0
fi

if ! ssh -i "$SSH_KEY" "$REMOTE_HOST" "
set -e
cp $REMOTE_CONFIG ${REMOTE_CONFIG}.bak
sudo sed -i '/^$LIST_KEY:/a\\- $URL' $REMOTE_CONFIG
sudo chown valme:valme $REMOTE_CONFIG
if ! python3 -c \"import yaml; yaml.safe_load(open('$REMOTE_CONFIG'))\"; then
    cp ${REMOTE_CONFIG}.bak $REMOTE_CONFIG
    echo 'YAML broke after insert, reverted' >&2
    exit 1
fi
"; then
    fail "Insert broke config YAML, reverted on remote"
    exit 1
fi
ok "Added to $LIST_KEY: $URL"
