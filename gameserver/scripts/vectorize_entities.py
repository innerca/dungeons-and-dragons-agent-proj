#!/usr/bin/env python3
"""
vectorize_entities.py - Incremental entity vectorization for ChromaDB.

Reads monster/npc/quest definitions from PostgreSQL and upserts them
into the sao_world_entities ChromaDB collection.

Uses collection.upsert() - safe to run repeatedly, never recreates.

Usage:
    python vectorize_entities.py [monsters|npcs|quests|all]
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

# Add src to path for chromadb_client imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gameserver.db.chromadb_client import init_chromadb, get_embedding_fn, COLLECTION_ENTITIES

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sao:sao_dev_password@localhost:5432/sao_game",
)

BATCH_SIZE = 50


def _build_monster_doc(row: dict) -> tuple[str, str, dict]:
    """Build (id, document, metadata) for a monster."""
    doc_id = f"monster_{row['id']}"
    doc = (
        f"怪物: {row['name']} ({row.get('name_en', '')})\n"
        f"类型: {row['monster_type']} | 楼层: {row['floor']} | 区域: {row.get('area', '未知')}\n"
        f"等级: {row['level_min']}-{row['level_max']} | HP: {row['hp']} | ATK: {row['atk']} | DEF: {row['defense']} | AC: {row['ac']}\n"
        f"行为: {row.get('behavior_type', 'aggressive')} | 弱点: {row.get('weaknesses', '无')}\n"
        f"经验: {row['exp_reward']} | 珂尔: {row.get('col_reward_min', 0)}-{row.get('col_reward_max', 0)}\n"
        f"{row.get('description', '')}"
    )
    metadata = {
        "entity_type": "monster",
        "entity_id": row["id"],
        "floor": row["floor"],
        "name": row["name"],
    }
    return doc_id, doc, metadata


def _build_npc_doc(row: dict) -> tuple[str, str, dict]:
    """Build (id, document, metadata) for an NPC."""
    doc_id = f"npc_{row['id']}"
    doc = (
        f"NPC: {row['name']} ({row.get('name_en', '')})\n"
        f"类型: {row['npc_type']} | 楼层: {row['floor']} | 位置: {row.get('location', '未知')}\n"
        f"阵营: {row.get('faction', '无')} | 初始好感: {row.get('initial_relationship', 0)}\n"
        f"外貌: {row.get('appearance', '')}\n"
        f"性格: {row.get('personality', '')}\n"
        f"说话风格: {row.get('dialog_style', '')}\n"
        f"{row.get('description', '')}"
    )
    metadata = {
        "entity_type": "npc",
        "entity_id": row["id"],
        "floor": row["floor"],
        "name": row["name"],
    }
    return doc_id, doc, metadata


def _build_quest_doc(row: dict) -> tuple[str, str, dict]:
    """Build (id, document, metadata) for a quest."""
    doc_id = f"quest_{row['id']}"
    doc = (
        f"任务: {row['name']}\n"
        f"类型: {row['quest_type']} | 楼层: {row['floor']} | 难度: {row.get('difficulty', 'normal')}\n"
        f"章节: {row.get('chapter', 1)}/{row.get('total_chapters', 1)}\n"
        f"{row.get('description', '')}"
    )
    metadata = {
        "entity_type": "quest",
        "entity_id": row["id"],
        "floor": row["floor"],
        "name": row["name"],
    }
    return doc_id, doc, metadata


async def vectorize(target: str):
    """Read entities from PG and upsert into ChromaDB."""
    # Init ChromaDB
    chromadb_path = str(Path(__file__).resolve().parent.parent / "data" / "chromadb")
    init_chromadb(chromadb_path)

    import chromadb
    client = chromadb.PersistentClient(path=chromadb_path)
    collection = client.get_or_create_collection(
        name=COLLECTION_ENTITIES,
        embedding_function=get_embedding_fn(),
        metadata={"description": "SAO world entities: monsters, NPCs, quests"},
    )

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)

    try:
        targets = [target] if target != "all" else ["monsters", "npcs", "quests"]
        total_upserted = 0

        for t in targets:
            if t == "monsters":
                rows = await pool.fetch("SELECT * FROM monster_definitions ORDER BY floor, id")
                builder = _build_monster_doc
            elif t == "npcs":
                rows = await pool.fetch("SELECT * FROM npc_definitions ORDER BY floor, id")
                builder = _build_npc_doc
            elif t == "quests":
                rows = await pool.fetch("SELECT * FROM quest_definitions ORDER BY floor, id")
                builder = _build_quest_doc
            else:
                continue

            if not rows:
                logger.warning(f"No {t} found in PostgreSQL, skipping")
                continue

            ids, documents, metadatas = [], [], []
            for row in rows:
                doc_id, doc, meta = builder(dict(row))
                ids.append(doc_id)
                documents.append(doc)
                metadatas.append(meta)

            # Batch upsert
            for i in range(0, len(ids), BATCH_SIZE):
                end = min(i + BATCH_SIZE, len(ids))
                collection.upsert(
                    ids=ids[i:end],
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                )

            logger.info(f"Upserted {len(ids)} {t} into ChromaDB")
            total_upserted += len(ids)

        logger.info(f"Vectorization complete. {total_upserted} entities in collection "
                     f"(total: {collection.count()})")
    finally:
        await pool.close()


def main():
    parser = argparse.ArgumentParser(description="Vectorize game entities into ChromaDB (upsert)")
    parser.add_argument("target", choices=["monsters", "npcs", "quests", "all"], default="all",
                        nargs="?")
    args = parser.parse_args()
    asyncio.run(vectorize(args.target))


if __name__ == "__main__":
    main()
