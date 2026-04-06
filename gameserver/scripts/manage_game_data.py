#!/usr/bin/env python3
"""
manage_game_data.py - Incremental Game Data Management Tool

Syncs YAML entity files (data/entities/) to PostgreSQL using UPSERT.
NEVER regenerates data - always incremental INSERT ... ON CONFLICT DO UPDATE.

Usage:
    python manage_game_data.py sync [monsters|npcs|quests|all]
    python manage_game_data.py show [monsters|npcs|quests] [--floor N]
    python manage_game_data.py delete <entity_type> <entity_id>
    python manage_game_data.py migrate

Examples:
    python manage_game_data.py sync all                 # Sync everything
    python manage_game_data.py sync monsters             # Sync monsters only
    python manage_game_data.py show npcs --floor 1       # Show Floor 1 NPCs
    python manage_game_data.py delete monsters f1_boar   # Delete one monster
    python manage_game_data.py migrate                   # Run v0500 migration DDL
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import asyncpg
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTITIES_DIR = PROJECT_ROOT / "data" / "entities"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sao:sao_dev_password@localhost:5432/sao_game",
)


# ──────────────────────────────────────────────
# YAML Loading
# ──────────────────────────────────────────────

def load_yaml_entities(entity_type: str) -> list[dict]:
    """Load all YAML files for a given entity type."""
    pattern = f"*_{entity_type}.yaml"
    files = sorted(ENTITIES_DIR.glob(pattern))
    if not files:
        logger.warning(f"No YAML files matching {pattern} in {ENTITIES_DIR}")
        return []

    entities = []
    for f in files:
        logger.info(f"Loading {f.name}")
        with open(f) as fh:
            data = yaml.safe_load(fh)
        key = entity_type
        if key in data:
            entities.extend(data[key])
        else:
            logger.warning(f"No '{key}' key found in {f.name}")
    return entities


# ──────────────────────────────────────────────
# Upsert Functions
# ──────────────────────────────────────────────

async def upsert_monsters(pool: asyncpg.Pool, monsters: list[dict]) -> int:
    """Upsert monster definitions. Returns count of affected rows."""
    sql = """
    INSERT INTO monster_definitions (
        id, name, name_en, monster_type, floor, area,
        level_min, level_max, hp, atk, defense, ac,
        exp_reward, col_reward_min, col_reward_max,
        behavior_type, weaknesses, abilities_json, loot_table_json, description
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        name_en = EXCLUDED.name_en,
        monster_type = EXCLUDED.monster_type,
        floor = EXCLUDED.floor,
        area = EXCLUDED.area,
        level_min = EXCLUDED.level_min,
        level_max = EXCLUDED.level_max,
        hp = EXCLUDED.hp,
        atk = EXCLUDED.atk,
        defense = EXCLUDED.defense,
        ac = EXCLUDED.ac,
        exp_reward = EXCLUDED.exp_reward,
        col_reward_min = EXCLUDED.col_reward_min,
        col_reward_max = EXCLUDED.col_reward_max,
        behavior_type = EXCLUDED.behavior_type,
        weaknesses = EXCLUDED.weaknesses,
        abilities_json = EXCLUDED.abilities_json,
        loot_table_json = EXCLUDED.loot_table_json,
        description = EXCLUDED.description,
        updated_at = now()
    """
    count = 0
    async with pool.acquire() as conn:
        for m in monsters:
            await conn.execute(
                sql,
                m["id"], m["name"], m.get("name_en"),
                m["monster_type"], m["floor"], m.get("area"),
                m.get("level_min", 1), m.get("level_max", 1),
                m["hp"], m["atk"], m["defense"], m.get("ac", 10),
                m.get("exp_reward", 10),
                m.get("col_reward_min", 0), m.get("col_reward_max", 0),
                m.get("behavior_type", "aggressive"),
                m.get("weaknesses"),
                json.dumps(m.get("abilities_json", []), ensure_ascii=False),
                json.dumps(m.get("loot_table_json", []), ensure_ascii=False),
                m.get("description", "").strip(),
            )
            count += 1
            logger.info(f"  Upserted monster: {m['id']} ({m['name']})")
    return count


async def upsert_npcs(pool: asyncpg.Pool, npcs: list[dict]) -> int:
    """Upsert NPC definitions. Returns count of affected rows."""
    sql = """
    INSERT INTO npc_definitions (
        id, name, name_en, npc_type, floor, location, faction,
        appearance, personality, dialog_style,
        services_json, related_quests_json,
        initial_relationship, description
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        name_en = EXCLUDED.name_en,
        npc_type = EXCLUDED.npc_type,
        floor = EXCLUDED.floor,
        location = EXCLUDED.location,
        faction = EXCLUDED.faction,
        appearance = EXCLUDED.appearance,
        personality = EXCLUDED.personality,
        dialog_style = EXCLUDED.dialog_style,
        services_json = EXCLUDED.services_json,
        related_quests_json = EXCLUDED.related_quests_json,
        initial_relationship = EXCLUDED.initial_relationship,
        description = EXCLUDED.description,
        updated_at = now()
    """
    count = 0
    async with pool.acquire() as conn:
        for n in npcs:
            await conn.execute(
                sql,
                n["id"], n["name"], n.get("name_en"),
                n["npc_type"], n["floor"], n.get("location"),
                n.get("faction"),
                n.get("appearance", "").strip(),
                n.get("personality", "").strip(),
                n.get("dialog_style", ""),
                json.dumps(n.get("services_json", {}), ensure_ascii=False),
                json.dumps(n.get("related_quests_json", []), ensure_ascii=False),
                n.get("initial_relationship", 0),
                n.get("description", "").strip(),
            )
            count += 1
            logger.info(f"  Upserted NPC: {n['id']} ({n['name']})")
    return count


async def upsert_quests(pool: asyncpg.Pool, quests: list[dict]) -> int:
    """Upsert quest definitions. Returns count of affected rows."""
    sql = """
    INSERT INTO quest_definitions (
        id, name, quest_type, floor, chapter, total_chapters,
        difficulty, is_repeatable,
        prerequisites_json, trigger_json, objectives_json,
        rewards_json, failure_json, choices_json, description
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        quest_type = EXCLUDED.quest_type,
        floor = EXCLUDED.floor,
        chapter = EXCLUDED.chapter,
        total_chapters = EXCLUDED.total_chapters,
        difficulty = EXCLUDED.difficulty,
        is_repeatable = EXCLUDED.is_repeatable,
        prerequisites_json = EXCLUDED.prerequisites_json,
        trigger_json = EXCLUDED.trigger_json,
        objectives_json = EXCLUDED.objectives_json,
        rewards_json = EXCLUDED.rewards_json,
        failure_json = EXCLUDED.failure_json,
        choices_json = EXCLUDED.choices_json,
        description = EXCLUDED.description,
        updated_at = now()
    """
    count = 0
    async with pool.acquire() as conn:
        for q in quests:
            await conn.execute(
                sql,
                q["id"], q["name"], q["quest_type"], q["floor"],
                q.get("chapter", 1), q.get("total_chapters", 1),
                q.get("difficulty", "normal"),
                q.get("is_repeatable", False),
                json.dumps(q.get("prerequisites_json", {}), ensure_ascii=False),
                json.dumps(q.get("trigger_json", {}), ensure_ascii=False),
                json.dumps(q.get("objectives_json", []), ensure_ascii=False),
                json.dumps(q.get("rewards_json", {}), ensure_ascii=False),
                json.dumps(q.get("failure_json", {}), ensure_ascii=False),
                json.dumps(q.get("choices_json", []), ensure_ascii=False),
                q.get("description", "").strip(),
            )
            count += 1
            logger.info(f"  Upserted quest: {q['id']} ({q['name']})")
    return count


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

async def cmd_sync(args):
    """Sync YAML entities to PostgreSQL via upsert."""
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
    try:
        targets = [args.target] if args.target != "all" else ["monsters", "npcs", "quests"]
        total = 0
        for t in targets:
            entities = load_yaml_entities(t)
            if not entities:
                continue
            logger.info(f"Syncing {len(entities)} {t}...")
            if t == "monsters":
                total += await upsert_monsters(pool, entities)
            elif t == "npcs":
                total += await upsert_npcs(pool, entities)
            elif t == "quests":
                total += await upsert_quests(pool, entities)
        logger.info(f"Sync complete. {total} entities upserted.")
    finally:
        await pool.close()


async def cmd_show(args):
    """Show entities from PostgreSQL."""
    table_map = {
        "monsters": "monster_definitions",
        "npcs": "npc_definitions",
        "quests": "quest_definitions",
    }
    table = table_map[args.target]
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        sql = f"SELECT id, name, floor FROM {table}"
        params = []
        if args.floor:
            sql += " WHERE floor = $1"
            params.append(args.floor)
        sql += " ORDER BY floor, id"
        rows = await pool.fetch(sql, *params)
        if not rows:
            print(f"No {args.target} found.")
            return
        print(f"\n{'ID':<30} {'Name':<25} {'Floor'}")
        print("-" * 65)
        for r in rows:
            print(f"{r['id']:<30} {r['name']:<25} {r['floor']}")
        print(f"\nTotal: {len(rows)}")
    finally:
        await pool.close()


async def cmd_delete(args):
    """Delete a single entity by ID."""
    table_map = {
        "monsters": "monster_definitions",
        "npcs": "npc_definitions",
        "quests": "quest_definitions",
    }
    table = table_map[args.target]
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        result = await pool.execute(f"DELETE FROM {table} WHERE id = $1", args.entity_id)
        if "DELETE 1" in result:
            logger.info(f"Deleted {args.target[:-1]}: {args.entity_id}")
        else:
            logger.warning(f"Entity not found: {args.entity_id}")
    finally:
        await pool.close()


async def cmd_migrate(args):
    """Run v0500 migration DDL."""
    migration_file = MIGRATIONS_DIR / "v0500_schema.sql"
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)

    sql = migration_file.read_text()
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        await pool.execute(sql)
        logger.info("v0500 migration applied successfully.")
    finally:
        await pool.close()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SAO Game Data Manager - Incremental UPSERT tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="Sync YAML entities to PostgreSQL (upsert)")
    p_sync.add_argument("target", choices=["monsters", "npcs", "quests", "all"], default="all")

    # show
    p_show = sub.add_parser("show", help="Show entities from PostgreSQL")
    p_show.add_argument("target", choices=["monsters", "npcs", "quests"])
    p_show.add_argument("--floor", type=int, help="Filter by floor number")

    # delete
    p_delete = sub.add_parser("delete", help="Delete a single entity by ID")
    p_delete.add_argument("target", choices=["monsters", "npcs", "quests"])
    p_delete.add_argument("entity_id", help="The entity ID to delete")

    # migrate
    sub.add_parser("migrate", help="Run v0500 schema migration")

    args = parser.parse_args()

    cmd_map = {
        "sync": cmd_sync,
        "show": cmd_show,
        "delete": cmd_delete,
        "migrate": cmd_migrate,
    }

    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
