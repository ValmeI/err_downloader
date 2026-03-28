#!/bin/bash
# Deploy ERR Downloader to homelab server
# Can be run standalone or called from homelab/deploy.sh

set -euo pipefail

# --- Configuration ---
REMOTE_HOST="${HOMELAB_HOST:-homelab.local}"
SSH_KEY="${HOMELAB_SSH_KEY:-$HOME/.ssh/id_homelab}"
REMOTE_APP_DIR="/opt/err_downloader"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false

# --- Logging ---
_ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()         { echo "$(_ts)  $*"; }
log_success() { echo "$(_ts)  OK: $*"; }
log_error()   { echo "$(_ts)  ERROR: $*" >&2; }

# --- Remote execution helpers ---
remote_exec() {
    local cmd="$1"
    local log_msg="${2:-}"

    if [[ "$DRY_RUN" == true ]]; then
        [[ -n "$log_msg" ]] && log "$log_msg"
        echo "[DRY RUN] Would execute: $cmd"
        return 0
    fi

    [[ -n "$log_msg" ]] && log "$log_msg"
    ssh -i "$SSH_KEY" "$REMOTE_HOST" "$cmd"
}

remote_exec_sudo() {
    local cmd="$1"
    local log_msg="${2:-}"

    if [[ "$DRY_RUN" == true ]]; then
        [[ -n "$log_msg" ]] && log "$log_msg"
        echo "[DRY RUN] Would execute (sudo): $cmd"
        return 0
    fi

    [[ -n "$log_msg" ]] && log "$log_msg"
    ssh -i "$SSH_KEY" "$REMOTE_HOST" "sudo $cmd"
}

remote_copy() {
    local src="$1"
    local dst="$2"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would copy: $src -> $REMOTE_HOST:$dst"
        return 0
    fi

    scp -i "$SSH_KEY" "$src" "$REMOTE_HOST:$dst"
}

# --- Usage ---
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy ERR Downloader to homelab server.

OPTIONS:
    -h, --help       Show this help message
    -n, --dry-run    Show what would be deployed without applying
    --host HOST      Override remote host (default: homelab.local)
EOF
    exit 0
}

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        -n|--dry-run) DRY_RUN=true; shift ;;
        --host) REMOTE_HOST="$2"; shift 2 ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

# --- Main deployment ---
log "Deploying ERR Downloader to $REMOTE_HOST..."

# Preflight checks
if [[ ! -f "$SSH_KEY" ]]; then
    log_error "SSH key not found: $SSH_KEY"
    exit 1
fi

if [[ "$DRY_RUN" != true ]]; then
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$REMOTE_HOST" "true" 2>/dev/null; then
        log_error "Cannot connect to $REMOTE_HOST"
        exit 1
    fi
    log_success "SSH connectivity OK"
fi

# Ensure remote repo exists
if ! remote_exec "test -d $REMOTE_APP_DIR/.git" > /dev/null 2>&1; then
    log_error "ERR Downloader repository not found at $REMOTE_APP_DIR"
    log "Clone it first: sudo git clone https://github.com/ValmeI/err_downloader $REMOTE_APP_DIR"
    exit 1
fi

# Pull latest source code
if ! remote_exec "cd $REMOTE_APP_DIR && git pull" \
    "Pulling latest code from GitHub..."; then
    log_error "Failed to pull - fix conflicts on server first"
    exit 1
fi

# Deploy runtime script
remote_copy "$SCRIPT_DIR/run_downloader.sh" "/tmp/run_downloader.sh"
remote_exec_sudo "cp /tmp/run_downloader.sh $REMOTE_APP_DIR/run_downloader.sh"
remote_exec_sudo "chmod +x $REMOTE_APP_DIR/run_downloader.sh"
remote_exec_sudo "chown valme:valme $REMOTE_APP_DIR/run_downloader.sh"
remote_exec "rm -f /tmp/run_downloader.sh"
log_success "Runtime script deployed"

# Deploy config with path adaptation
if [[ ! -f "$SCRIPT_DIR/config.yaml" ]]; then
    log_error "Config not found: $SCRIPT_DIR/config.yaml"
    log "Copy config.example.yaml to config.yaml and configure it"
    exit 1
fi

# Convert macOS paths to Linux paths
local_tmp=$(mktemp)
sed 's|/Volumes/NAS_Files|/media/nas|g' "$SCRIPT_DIR/config.yaml" > "$local_tmp"
remote_copy "$local_tmp" "/tmp/err_config.yaml"
rm -f "$local_tmp"
remote_exec_sudo "cp /tmp/err_config.yaml $REMOTE_APP_DIR/config.yaml"
remote_exec_sudo "chown valme:valme $REMOTE_APP_DIR/config.yaml"
remote_exec "rm -f /tmp/err_config.yaml"
log_success "Config deployed (paths adapted)"

# Add cron job if not exists (6:00 and 18:00 daily)
if ! remote_exec "crontab -l 2>/dev/null | grep -q 'err_downloader/run_downloader.sh'"; then
    remote_exec "(crontab -l 2>/dev/null; echo -e '\n# ERR Downloader - kaivitub igal paeval kell 6:00 ja 18:00\n0 6,18 * * * $REMOTE_APP_DIR/run_downloader.sh') | crontab -" \
        "Adding cron job (6:00 and 18:00)..."
    log_success "Cron job added"
else
    log_success "Cron job already exists"
fi

log_success "ERR Downloader deployed successfully"
