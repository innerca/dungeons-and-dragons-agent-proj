#!/usr/bin/env bash
set -euo pipefail

# SAO Progressive DND - One-click Stop Script
# Auto-detects running mode and stops all services.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[STOP]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
info() { echo -e "${CYAN}[INFO]${NC} $*"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SAO Progressive DND - Stop Script      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

stopped=false

# ---------- Stop Docker services ----------
if command -v docker &>/dev/null && docker compose ps --quiet 2>/dev/null | grep -q .; then
    log "Stopping Docker Compose services..."
    docker compose down
    stopped=true
    info "Docker services stopped."
fi

# ---------- Stop local services ----------
stop_pid_file() {
    local name="$1" pid_file="$2"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping $name (PID $pid)..."
            kill "$pid" 2>/dev/null || true
            # Wait up to 5 seconds
            local i=0
            while kill -0 "$pid" 2>/dev/null && [ $i -lt 50 ]; do
                sleep 0.1
                i=$((i + 1))
            done
            if kill -0 "$pid" 2>/dev/null; then
                warn "$name did not stop gracefully, force killing..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            stopped=true
        fi
        rm -f "$pid_file"
    fi
}

stop_pid_file "GameServer" /tmp/sao_gameserver.pid
stop_pid_file "Gateway" /tmp/sao_gateway.pid
stop_pid_file "Frontend" /tmp/sao_frontend.pid

# Also try to kill by port if PID files are missing
kill_by_port() {
    local port="$1" name="$2"
    local pid
    pid=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        log "Stopping $name on port $port (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        stopped=true
    fi
}

# Only kill by port if no PID files were found
if [ "$stopped" = false ]; then
    kill_by_port 50051 "GameServer"
    kill_by_port 8080 "Gateway"
    kill_by_port 5173 "Frontend (dev)"
fi

if [ "$stopped" = true ]; then
    echo ""
    log "All services stopped."
else
    info "No running services found."
fi
