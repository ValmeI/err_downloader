#!/bin/bash
# ERR Downloader Deployment Script
# Updates homelab server with latest code and config

set -e

HOMELAB="valme@homelab.local"
SSH_KEY="$HOME/.ssh/id_homelab"
APP_DIR="/opt/err_downloader"
BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [ ! -f "config.yaml" ]; then
        log_error "config.yaml not found in current directory"
        exit 1
    fi
    
    if [ ! -f "$SSH_KEY" ]; then
        log_error "SSH key not found: $SSH_KEY"
        exit 1
    fi
    
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$HOMELAB" "exit" 2>/dev/null; then
        log_error "Cannot connect to homelab server"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
    echo ""
}

create_backup() {
    log_info "Creating backup..."
    ssh -i "$SSH_KEY" "$HOMELAB" "mkdir -p $BACKUP_DIR && \
        cd $APP_DIR && \
        tar -czf $BACKUP_DIR/backup_$TIMESTAMP.tar.gz \
        --exclude='venv' \
        --exclude='logs' \
        --exclude='__pycache__' \
        --exclude='backups' \
        . 2>/dev/null || true"
    
    ssh -i "$SSH_KEY" "$HOMELAB" "ls -lh $BACKUP_DIR/backup_$TIMESTAMP.tar.gz 2>/dev/null" || {
        log_warning "Backup creation skipped or failed"
        return
    }
    
    log_success "Backup created: backup_$TIMESTAMP.tar.gz"
    
    # Keep only last 5 backups
    ssh -i "$SSH_KEY" "$HOMELAB" "cd $BACKUP_DIR && ls -t backup_*.tar.gz | tail -n +6 | xargs -r rm" || true
    echo ""
}

deploy_code() {
    log_info "Pulling latest code from GitHub..."
    ssh -i "$SSH_KEY" "$HOMELAB" "cd $APP_DIR && git reset --hard HEAD && git clean -fd && git pull origin main"
    log_success "Code updated"
    echo ""
}

deploy_config() {
    log_info "Copying config.yaml to homelab..."
    scp -q -i "$SSH_KEY" config.yaml "$HOMELAB:$APP_DIR/config.yaml"
    log_success "Config updated"
    echo ""
}

update_dependencies() {
    log_info "Updating dependencies..."
    ssh -i "$SSH_KEY" "$HOMELAB" "cd $APP_DIR && source venv/bin/activate && pip install -r requirements.txt --upgrade --quiet"
    log_success "Dependencies updated"
    echo ""
}

restart_service() {
    log_info "Checking for running service..."
    
    local pid=$(ssh -i "$SSH_KEY" "$HOMELAB" "pgrep -f 'python.*main.py' || true")
    
    if [ -n "$pid" ]; then
        log_info "Service is running (PID: $pid), restarting..."
        ssh -i "$SSH_KEY" "$HOMELAB" "pkill -f 'python.*main.py' || true"
        sleep 2
        log_success "Service stopped"
    else
        log_info "Service not running, no restart needed"
    fi
    echo ""
}

show_status() {
    log_info "Current status:"
    ssh -i "$SSH_KEY" "$HOMELAB" "cd $APP_DIR && git log -1 --oneline && echo '' && pgrep -f 'python.*main.py' && echo 'Service: RUNNING' || echo 'Service: STOPPED'"
    echo ""
}

rollback() {
    log_warning "Rolling back to previous version..."
    local latest_backup=$(ssh -i "$SSH_KEY" "$HOMELAB" "ls -t $BACKUP_DIR/backup_*.tar.gz 2>/dev/null | head -1")
    
    if [ -z "$latest_backup" ]; then
        log_error "No backup found for rollback"
        return 1
    fi
    
    ssh -i "$SSH_KEY" "$HOMELAB" "cd $APP_DIR && tar -xzf $latest_backup"
    log_success "Rolled back to: $(basename $latest_backup)"
}

trap 'log_error "Deployment failed! Run with --rollback to restore previous version."; exit 1' ERR

# Parse arguments
SKIP_CONFIRMATION=false
ROLLBACK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            SKIP_CONFIRMATION=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        *)
            echo "Usage: $0 [-y|--yes] [--rollback]"
            echo "  -y, --yes     Skip confirmation prompt"
            echo "  --rollback    Rollback to previous backup"
            exit 1
            ;;
    esac
done

echo ""
log_info "ERR Downloader Deployment Script"
echo "=================================================="
echo ""

if [ "$ROLLBACK" = true ]; then
    rollback
    exit 0
fi

check_prerequisites

if [ "$SKIP_CONFIRMATION" = false ]; then
    log_warning "This will reset any local changes on homelab.local. Continue? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    echo ""
fi

create_backup
deploy_code
deploy_config
update_dependencies
restart_service

log_success "Deployment complete!"
echo ""
show_status

echo "Useful commands:"
echo "  View logs:    ssh $HOMELAB 'tail -f $APP_DIR/logs/downloader.log'"
echo "  Rollback:     ./deploy.sh --rollback"
echo ""
