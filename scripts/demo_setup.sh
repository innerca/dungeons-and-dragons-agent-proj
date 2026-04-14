#!/bin/bash
set -e

# SAO Progressive DND - Demo Data Setup Script
# 一键初始化 Demo 数据

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[DEMO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      SAO Progressive DND - Demo Setup    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    error "DATABASE_URL 环境变量未设置"
    info "示例: export DATABASE_URL=postgresql://sao:sao_dev_password@localhost:5432/sao_game"
    exit 1
fi

# 检查 psql 是否可用
if ! command -v psql &>/dev/null; then
    error "psql 命令未找到，请安装 PostgreSQL 客户端"
    exit 1
fi

# ============================================
# 1. 执行 SQL seed（测试账号和角色数据）
# ============================================
log "[1/3] 导入测试账号和角色数据..."

if [ -f "$PROJECT_ROOT/data/demo/seed_players.sql" ]; then
    psql "$DATABASE_URL" -f "$PROJECT_ROOT/data/demo/seed_players.sql" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        log "测试数据导入成功"
    else
        error "测试数据导入失败"
        exit 1
    fi
else
    error "找不到 seed_players.sql 文件"
    exit 1
fi

# ============================================
# 2. 导入 sample chunks 到 ChromaDB
# ============================================
log "[2/3] 导入演示文本到向量库..."

cd "$PROJECT_ROOT/gameserver"

uv run python -c "
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, 'src')

from gameserver.db.chromadb_client import init_chromadb, get_embedding_fn, COLLECTION_NOVELS

# 读取 sample chunks
chunks_path = Path('$PROJECT_ROOT') / 'data' / 'demo' / 'sample_chunks.json'
if not chunks_path.exists():
    print(f'错误: 找不到 {chunks_path}')
    sys.exit(1)

with open(chunks_path, 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f'  读取到 {len(chunks)} 条文本块')

# 初始化 ChromaDB
chromadb_path = str(Path('$PROJECT_ROOT') / 'gameserver' / 'data' / 'chromadb')
client = init_chromadb(chromadb_path)
embedding_fn = get_embedding_fn()

# 获取或创建集合
collection = client.get_or_create_collection(
    name=COLLECTION_NOVELS,
    embedding_function=embedding_fn,
    metadata={'description': 'SAO Progressive novels + demo chunks'}
)

# 准备数据
all_ids = []
all_documents = []
all_metadatas = []

for chunk in chunks:
    all_ids.append(chunk['id'])
    all_documents.append(chunk['text'])
    # 确保 metadata 值是 ChromaDB 支持的类型
    metadata = {
        'source': chunk['metadata'].get('source', 'demo'),
        'chunk_index': chunk['metadata'].get('chunk_index', 0),
        'aincrad_layer': chunk['metadata'].get('aincrad_layer', 1),
        'category': chunk['metadata'].get('category', 'general')
    }
    all_metadatas.append(metadata)

# 检查是否已存在这些 chunks
existing_count = 0
for doc_id in all_ids:
    try:
        result = collection.get(ids=[doc_id])
        if result and result['ids']:
            existing_count += 1
    except Exception:
        pass

if existing_count > 0:
    print(f'  发现 {existing_count} 条已存在的文本块，将跳过')

# 添加数据（跳过已存在的）
new_ids = []
new_documents = []
new_metadatas = []

for i, doc_id in enumerate(all_ids):
    try:
        result = collection.get(ids=[doc_id])
        if not result or not result['ids']:
            new_ids.append(doc_id)
            new_documents.append(all_documents[i])
            new_metadatas.append(all_metadatas[i])
    except Exception:
        new_ids.append(doc_id)
        new_documents.append(all_documents[i])
        new_metadatas.append(all_metadatas[i])

if new_ids:
    collection.add(
        ids=new_ids,
        documents=new_documents,
        metadatas=new_metadatas
    )
    print(f'  成功导入 {len(new_ids)} 条新文本块')
else:
    print('  所有文本块已存在，无需导入')

print(f'  集合 {COLLECTION_NOVELS} 现有 {collection.count()} 条文档')
" || {
    error "文本块导入失败"
    exit 1
}

# ============================================
# 3. 向量化游戏实体
# ============================================
log "[3/3] 向量化游戏实体..."

if [ -f "$PROJECT_ROOT/gameserver/scripts/vectorize_entities.py" ]; then
    cd "$PROJECT_ROOT/gameserver"
    HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}" uv run python scripts/vectorize_entities.py || {
        warn "实体向量化执行失败，但 Demo 数据已部分导入"
    }
else
    warn "找不到 vectorize_entities.py 脚本，跳过实体向量化"
fi

# ============================================
# 完成
# ============================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Demo 数据初始化完成！              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
info "测试账号:"
echo "  - demo / demo123      (等级3角色，有装备和任务进度)"
echo "  - testplayer / test123 (等级1新手角色)"
echo ""
info "数据内容:"
echo "  - 2个测试账号和角色"
echo "  - 角色装备、剑技、任务进度"
echo "  - NPC 关系数据"
echo "  - 20条演示文本块"
echo ""
