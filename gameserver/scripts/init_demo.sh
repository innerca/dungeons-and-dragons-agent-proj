#!/bin/bash
# Docker 容器内的 Demo 数据初始化脚本
# 在 GameServer 容器启动后自动执行

set -e

echo "[INFO] Starting demo data initialization..."

# 等待 PostgreSQL 就绪
echo "[INFO] Waiting for PostgreSQL..."
until PGPASSWORD="${POSTGRES_PASSWORD:-sao_dev_password}" psql -h postgres -U sao -d sao_game -c "SELECT 1" >/dev/null 2>&1; do
    echo "[INFO] PostgreSQL not ready, waiting..."
    sleep 2
done
echo "[INFO] PostgreSQL is ready"

# 检查是否已有玩家数据
PLAYER_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-sao_dev_password}" psql -h postgres -U sao -d sao_game -t -c "SELECT COUNT(*) FROM players;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$PLAYER_COUNT" -gt 0 ]; then
    echo "[INFO] Found $PLAYER_COUNT existing players, skipping demo initialization"
    exit 0
fi

echo "[INFO] Database is empty, initializing demo data..."

# 1. 导入 SQL seed 数据
echo "[1/3] Importing test accounts and characters..."
PGPASSWORD="${POSTGRES_PASSWORD:-sao_dev_password}" psql -h postgres -U sao -d sao_game -f /app/data/demo/seed_players.sql

# 2. 导入 ChromaDB 文本块
echo "[2/3] Importing demo text chunks to vector database..."
cd /app
uv run python -c "
import json
import sys
from pathlib import Path

sys.path.insert(0, 'src')

from gameserver.db.chromadb_client import init_chromadb, get_embedding_fn, COLLECTION_NOVELS

# 读取 sample chunks
chunks_path = Path('/app/data/demo/sample_chunks.json')
if not chunks_path.exists():
    print(f'Error: {chunks_path} not found')
    sys.exit(1)

with open(chunks_path, 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f'  Read {len(chunks)} text chunks')

# 初始化 ChromaDB
chromadb_path = '/app/data/chromadb'
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
    metadata = {
        'source': chunk['metadata'].get('source', 'demo'),
        'chunk_index': chunk['metadata'].get('chunk_index', 0),
        'aincrad_layer': chunk['metadata'].get('aincrad_layer', 1),
        'category': chunk['metadata'].get('category', 'general')
    }
    all_metadatas.append(metadata)

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
    print(f'  Successfully imported {len(new_ids)} new text chunks')
else:
    print('  All text chunks already exist')

print(f'  Collection {COLLECTION_NOVELS} now has {collection.count()} documents')
" || {
    echo "[WARN] Text chunk import failed"
}

# 3. 向量化游戏实体
echo "[3/3] Vectorizing game entities..."
cd /app
HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}" uv run python scripts/vectorize_entities.py || {
    echo "[WARN] Entity vectorization failed, but demo data partially imported"
}

echo "[INFO] Demo data initialization completed!"
echo "[INFO] Test accounts:"
echo "  - demo / demo123      (Level 3 character with equipment and quests)"
echo "  - testplayer / test123 (Level 1 beginner character)"
