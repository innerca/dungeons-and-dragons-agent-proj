#!/usr/bin/env bash
set -euo pipefail

# SAO Progressive DND - One-click Start Script
# Auto-detects Docker or local mode, checks dependencies, starts all services.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[START]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }

# ---------- .env check ----------
check_env() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            warn ".env not found. Copying from .env.example..."
            cp .env.example .env
            warn "Please edit .env and fill in your API keys, then re-run this script."
            exit 1
        else
            error ".env and .env.example not found."
            exit 1
        fi
    fi
}

# ---------- Docker mode ----------
has_docker() {
    command -v docker &>/dev/null && docker info &>/dev/null 2>&1
}

start_docker() {
    log "Starting in Docker mode..."
    check_env

    if ! docker compose version &>/dev/null 2>&1; then
        error "docker compose not available. Install Docker Compose V2."
        exit 1
    fi

    log "Building and starting all services..."
    docker compose up --build -d

    log "Waiting for services to be healthy..."
    local retries=30
    while [ $retries -gt 0 ]; do
        if docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"' || \
           curl -sf http://localhost:8080/health &>/dev/null; then
            break
        fi
        sleep 2
        retries=$((retries - 1))
    done

    echo ""
    log "All services started!"
    info "Frontend:    http://localhost:3000"
    info "Gateway:     http://localhost:8080"
    info "GameServer:  localhost:50051 (gRPC)"
    info "PostgreSQL:  localhost:5432"
    info "Redis:       localhost:6379"
    echo ""
    info "View logs: docker compose logs -f"
    info "Stop:      ./scripts/stop.sh"
}

# ---------- Local mode dependency checks ----------
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        error "$1 is not installed. $2"
        return 1
    fi
    return 0
}

check_version() {
    local cmd="$1" min_ver="$2" install_hint="$3"
    local current
    current=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if [ -z "$current" ]; then
        warn "Could not detect $cmd version."
        return 0
    fi

    local cur_major cur_minor min_major min_minor
    cur_major=$(echo "$current" | cut -d. -f1)
    cur_minor=$(echo "$current" | cut -d. -f2)
    min_major=$(echo "$min_ver" | cut -d. -f1)
    min_minor=$(echo "$min_ver" | cut -d. -f2)

    if [ "$cur_major" -lt "$min_major" ] || { [ "$cur_major" -eq "$min_major" ] && [ "$cur_minor" -lt "$min_minor" ]; }; then
        error "$cmd version $current < required $min_ver. $install_hint"
        return 1
    fi
    info "$cmd $current (>= $min_ver)"
    return 0
}

check_local_deps() {
    local ok=true

    info "Checking local development dependencies..."
    echo ""

    check_cmd go "Install: https://go.dev/dl/" || ok=false
    [ "$ok" = true ] && { check_version go 1.22 "Install: https://go.dev/dl/" || ok=false; }

    check_cmd python3 "Install: https://www.python.org/downloads/" || ok=false
    [ "$ok" = true ] && { check_version python3 3.12 "Install: https://www.python.org/downloads/" || ok=false; }

    check_cmd node "Install: https://nodejs.org/" || ok=false
    [ "$ok" = true ] && { check_version node 18.0 "Install: https://nodejs.org/" || ok=false; }

    check_cmd uv "Install: curl -LsSf https://astral.sh/uv/install.sh | sh" || ok=false
    check_cmd protoc "Install: https://grpc.io/docs/protoc-installation/" || ok=false

    echo ""

    # Check for running PostgreSQL and Redis
    if ! pg_isready -h localhost -p 5432 &>/dev/null 2>&1; then
        warn "PostgreSQL not running on localhost:5432"
        if has_docker; then
            info "Starting PostgreSQL and Redis via Docker..."
            docker compose up -d postgres redis
            sleep 3
        else
            error "PostgreSQL required. Install and start it, or use Docker mode."
            ok=false
        fi
    else
        info "PostgreSQL running on localhost:5432"
    fi

    if ! redis-cli -h localhost -p 6379 ping &>/dev/null 2>&1; then
        warn "Redis not running on localhost:6379"
        if has_docker; then
            info "Starting Redis via Docker..."
            docker compose up -d redis
            sleep 2
        else
            error "Redis required. Install and start it, or use Docker mode."
            ok=false
        fi
    else
        info "Redis running on localhost:6379"
    fi

    if [ "$ok" = false ]; then
        error "Some dependencies are missing. Please install them and retry."
        exit 1
    fi

    echo ""
    log "All dependencies OK."
}

start_local() {
    log "Starting in local development mode..."
    check_env
    check_local_deps

    # Install dependencies if needed
    if [ ! -d "frontend/node_modules" ]; then
        info "Installing frontend dependencies..."
        (cd frontend && npm install)
    fi

    info "Syncing GameServer dependencies..."
    (cd gameserver && uv sync --quiet)

    # Generate gRPC code
    info "Generating gRPC code..."
    make proto-gen

    # Start services in background
    log "Starting GameServer on :50051..."
    (cd gameserver && PYTHONPATH=src:gen DATABASE_URL="${DATABASE_URL:-postgresql://sao:sao_dev_password@localhost:5432/sao_game}" REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" uv run python -m gameserver.main) &
    echo $! > /tmp/sao_gameserver.pid

    sleep 2

    log "Starting Gateway on :8080..."
    (cd gateway && REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" GO111MODULE=on go run cmd/gateway/main.go) &
    echo $! > /tmp/sao_gateway.pid

    sleep 1

    log "Starting Frontend on :5173..."
    (cd frontend && npm run dev -- --host) &
    echo $! > /tmp/sao_frontend.pid

    echo ""
    log "All services started!"
    info "Frontend:    http://localhost:5173"
    info "Gateway:     http://localhost:8080"
    info "GameServer:  localhost:50051 (gRPC)"
    echo ""
    info "Stop: ./scripts/stop.sh"
    echo ""

    # Wait for any child to exit
    wait
}

# ---------- Main ----------
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SAO Progressive DND - Start Script     ║${NC}"
echo -e "${CYAN}║   Version: $(cat VERSION 2>/dev/null || echo 'unknown')                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

MODE="${1:-auto}"

case "$MODE" in
    docker)
        start_docker
        ;;
    local)
        start_local
        ;;
    auto)
        if has_docker; then
            info "Docker detected. Using Docker mode."
            info "Use './scripts/start.sh local' to force local mode."
            echo ""
            start_docker
        else
            info "Docker not available. Using local mode."
            echo ""
            start_local
        fi
        ;;
    *)
        echo "Usage: $0 [docker|local|auto]"
        echo "  docker - Start with Docker Compose (recommended)"
        echo "  local  - Start locally (requires Go, Python, Node.js)"
        echo "  auto   - Auto-detect (default)"
        exit 1
        ;;
esac
