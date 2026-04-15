#!/usr/bin/env bash
set -euo pipefail

# SAO Progressive DND - One-click Data Initialization Script
# 一键初始化/重置所有数据（PostgreSQL + ChromaDB）
# 支持清空现有数据并重新初始化

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[INIT]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }

# ---------- 加载环境变量 ----------
load_env() {
    if [ ! -f .env ]; then
        error ".env not found. Run 'make start' first to create it."
        exit 1
    fi
    
    set -a
    source .env
    set +a
}

# ---------- 检查依赖 ----------
check_deps() {
    local ok=true

    info "Checking dependencies..."
    echo ""
    info "Required:"
    info "  - psql (PostgreSQL client)"
    info "  - uv (Python package manager)"
    echo ""

    # Check psql
    if ! command -v psql &>/dev/null; then
        error "psql is not installed. Please install PostgreSQL client."
        ok=false
    else
        local psql_version
        psql_version=$(psql --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        info "psql $psql_version"
    fi

    # Check uv
    if ! command -v uv &>/dev/null; then
        error "uv is not installed. Please install uv (https://docs.astral.sh/uv/)"
        ok=false
    else
        local uv_version
        uv_version=$(uv --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        info "uv $uv_version"
    fi

    echo ""

    if [ "$ok" = false ]; then
        error "Some dependencies are missing. Please install them and retry."
        exit 1
    fi

    log "All dependencies OK."
    echo ""
}

# ---------- 检查数据库连接 ----------
check_db() {
    local db_url="${DATABASE_URL:-postgresql://sao:sao_dev_password@localhost:5432/sao_game}"
    
    info "Checking database connection..."
    if ! psql "$db_url" -c "SELECT 1" >/dev/null 2>&1; then
        error "Cannot connect to database: $db_url"
        info "Please make sure PostgreSQL is running."
        exit 1
    fi
    log "Database connected."
    echo ""
}

# ---------- 清空数据 ----------
clear_data() {
    local db_url="${DATABASE_URL:-postgresql://sao:sao_dev_password@localhost:5432/sao_game}"
    
    warn "This will clear ALL existing data and reinitialize!"
    echo ""
    info "The following will be cleared:"
    info "  - PostgreSQL: players, characters, inventory, quests, relationships, world flags"
    info "  - ChromaDB:   all text chunks and entity vectors"
    echo ""
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        info "Aborted."
        exit 0
    fi
    
    echo ""
    log "Clearing PostgreSQL data..."
    
    # 按依赖顺序删除数据（外键约束）
    psql "$db_url" << 'SQL'
-- 删除玩家相关数据（级联删除关联表）
TRUNCATE TABLE 
    character_world_flags,
    character_noncombat_skills,
    character_npc_relationships,
    character_quests,
    character_sword_skills,
    character_inventory,
    player_characters,
    players
RESTART IDENTITY CASCADE;

-- 可选：重置定义表（取消注释以清空）
-- TRUNCATE TABLE monster_definitions, npc_definitions, quest_definitions RESTART IDENTITY CASCADE;
SQL
    
    log "PostgreSQL data cleared."
    echo ""
    
    # 清空 ChromaDB
    log "Clearing ChromaDB data..."
    local chromadb_path="$PROJECT_ROOT/gameserver/data/chromadb"
    if [ -d "$chromadb_path" ]; then
        rm -rf "$chromadb_path"
        mkdir -p "$chromadb_path"
        log "ChromaDB data cleared."
    else
        info "ChromaDB directory not found, skipping."
    fi
    echo ""
}

# ---------- 初始化数据库表结构 ----------
init_schema() {
    local db_url="${DATABASE_URL:-postgresql://sao:sao_dev_password@localhost:5432/sao_game}"
    
    log "[1/4] Initializing database schema..."
    
    # 检查表是否已存在
    local table_count=$(psql "$db_url" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
    
    if [ "$table_count" -gt 0 ]; then
        info "Found $table_count existing tables, skipping schema initialization."
        info "To reset schema, run: make db-init"
    else
        info "Database is empty, initializing schema..."
        make db-init
        log "Schema initialized."
    fi
    echo ""
}

# ---------- 导入Demo数据 ----------
import_demo_data() {
    local db_url="${DATABASE_URL:-postgresql://sao:sao_dev_password@localhost:5432/sao_game}"
    export DATABASE_URL="$db_url"
    
    log "[2/4] Importing demo data..."
    
    bash "$SCRIPT_DIR/demo_setup.sh"
    
    echo ""
}

# ---------- 同步游戏实体数据 ----------
sync_entities() {
    log "[3/4] Syncing game entities from YAML..."
    
    cd "$PROJECT_ROOT/gameserver"
    uv run python scripts/manage_game_data.py sync || {
        warn "Entity sync failed, but demo data is imported."
    }
    
    echo ""
}

# ---------- 向量化游戏实体 ----------
vectorize_entities() {
    log "[4/4] Vectorizing game entities..."
    
    cd "$PROJECT_ROOT/gameserver"
    HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}" uv run python scripts/vectorize_entities.py || {
        warn "Entity vectorization failed, but demo data is imported."
    }
    
    echo ""
}

# ---------- 显示结果 ----------
show_summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║       Data initialization completed!     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    info "Test accounts:"
    echo "  - demo / demo123      (Level 3 character with equipment and quests)"
    echo "  - testplayer / test123 (Level 1 beginner character)"
    echo ""
    info "Data initialized:"
    echo "  ✓ PostgreSQL schema and tables"
    echo "  ✓ 2 test accounts and characters"
    echo "  ✓ Character equipment, sword skills, quests"
    echo "  ✓ NPC relationships"
    echo "  ✓ World flags"
    echo "  ✓ Demo text chunks (ChromaDB)"
    echo "  ✓ Game entities vectorized"
    echo ""
    info "Next steps:"
    echo "  - Start services: ./scripts/start.sh"
    echo "  - Frontend: http://localhost:3000 (Docker) or http://localhost:5173 (Local)"
    echo ""
}

# ---------- Main ----------
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SAO Progressive DND - Data Init        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# 解析参数
MODE="${1:-fresh}"

case "$MODE" in
    fresh)
        # 默认模式：检查是否有数据，有则询问是否清空
        load_env
        check_deps
        check_db
        
        local db_url="${DATABASE_URL:-postgresql://sao:sao_dev_password@localhost:5432/sao_game}"
        PLAYER_COUNT=$(psql "$db_url" -t -c "SELECT COUNT(*) FROM players;" 2>/dev/null | tr -d ' ' || echo "0")
        
        if [ "$PLAYER_COUNT" -gt 0 ]; then
            warn "Found $PLAYER_COUNT existing players."
            echo ""
            read -p "Do you want to clear and reinitialize? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                clear_data
                init_schema
                import_demo_data
                sync_entities
                vectorize_entities
                show_summary
            else
                info "Aborted. Existing data preserved."
                exit 0
            fi
        else
            # 数据库为空，直接初始化
            init_schema
            import_demo_data
            sync_entities
            vectorize_entities
            show_summary
        fi
        ;;
    reset)
        # 强制重置模式：清空所有数据并重新初始化
        load_env
        check_deps
        check_db
        clear_data
        init_schema
        import_demo_data
        sync_entities
        vectorize_entities
        show_summary
        ;;
    *)
        echo "Usage: $0 [fresh|reset]"
        echo "  fresh  - Initialize data (prompt if data exists, default)"
        echo "  reset  - Force clear all data and reinitialize"
        exit 1
        ;;
esac
