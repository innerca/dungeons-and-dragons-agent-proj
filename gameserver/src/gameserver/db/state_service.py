"""Player state service: Redis cache (Layer 2) with PG fallback (Layer 1)."""

from __future__ import annotations

import json
import logging
import uuid

from gameserver.db.postgres import get_pg
from gameserver.db.redis_client import get_redis

logger = logging.getLogger(__name__)

# Redis key helpers
def _state_key(pid: str) -> str:
    return f"sao:player:{pid}:state"

def _history_key(pid: str) -> str:
    return f"sao:player:{pid}:chat:history"

def _summary_key(pid: str) -> str:
    return f"sao:player:{pid}:chat:summary"

def _auth_key(token: str) -> str:
    return f"sao:auth:token:{token}"


async def store_auth_token(token: str, player_id: str, ttl: int = 86400) -> None:
    """Store auth token → player_id mapping in Redis (TTL 24h)."""
    r = get_redis()
    await r.set(_auth_key(token), player_id, ex=ttl)


async def resolve_token(token: str) -> str | None:
    """Resolve auth token to player_id. Returns None if invalid/expired."""
    r = get_redis()
    return await r.get(_auth_key(token))


async def load_player_state(player_id: str) -> dict:
    """Load player state from Redis, fallback to PG if cache miss.

    Returns a flat dict of character attributes.
    """
    r = get_redis()
    key = _state_key(player_id)

    # Try Redis first
    cached = await r.hgetall(key)
    if cached:
        logger.debug("State cache hit for %s", player_id)
        return cached

    # Fallback to PG
    logger.info("State cache miss for %s, loading from PG", player_id)
    pool = get_pg()
    row = await pool.fetchrow(
        "SELECT * FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    if not row:
        return {}

    state = {
        "character_id": str(row["id"]),
        "name": row["name"],
        "level": str(row["level"]),
        "current_hp": str(row["current_hp"]),
        "max_hp": str(row["max_hp"]),
        "experience": str(row["experience"]),
        "exp_to_next": str(row["exp_to_next"]),
        "stat_str": str(row["stat_str"]),
        "stat_agi": str(row["stat_agi"]),
        "stat_vit": str(row["stat_vit"]),
        "stat_int": str(row["stat_int"]),
        "stat_dex": str(row["stat_dex"]),
        "stat_luk": str(row["stat_luk"]),
        "col": str(row["col"]),
        "current_floor": str(row["current_floor"]),
        "current_area": row["current_area"],
        "current_location": row["current_location"],
    }

    # Cache to Redis (TTL 2h)
    await r.hset(key, mapping=state)
    await r.expire(key, 7200)

    return state


async def save_player_state(player_id: str, changes: dict) -> None:
    """Write-Through: update Redis immediately, async persist to PG."""
    r = get_redis()
    key = _state_key(player_id)

    # Update Redis
    if changes:
        await r.hset(key, mapping={k: str(v) for k, v in changes.items()})
        await r.expire(key, 7200)

    # Persist to PG (sync for now, can be made async later)
    pg_updates = {}
    field_map = {
        "current_hp": "current_hp",
        "max_hp": "max_hp",
        "level": "level",
        "experience": "experience",
        "exp_to_next": "exp_to_next",
        "col": "col",
        "current_floor": "current_floor",
        "current_area": "current_area",
        "current_location": "current_location",
    }
    for k, v in changes.items():
        if k in field_map:
            pg_updates[field_map[k]] = int(v) if k not in ("current_area", "current_location") else v

    if pg_updates:
        pool = get_pg()
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(pg_updates))
        query = f"UPDATE player_characters SET {sets}, updated_at = now() WHERE player_id = $1"
        await pool.execute(query, uuid.UUID(player_id), *pg_updates.values())


# --- Conversation History (Redis Layer) ---

async def push_message(player_id: str, role: str, content: str) -> int:
    """Push a message to Redis chat history. Returns current length."""
    r = get_redis()
    key = _history_key(player_id)
    msg = json.dumps({"role": role, "content": content}, ensure_ascii=False)
    await r.lpush(key, msg)
    await r.ltrim(key, 0, 49)  # Keep max 50 messages
    await r.expire(key, 14400)  # TTL 4h
    length = await r.llen(key)

    # Also persist to PG
    pool = get_pg()
    await pool.execute(
        """INSERT INTO conversation_messages (player_id, role, content)
           VALUES ($1, $2, $3)""",
        uuid.UUID(player_id), role, content,
    )

    return length


async def get_recent_messages(player_id: str, count: int = 20) -> list[dict]:
    """Get recent messages from Redis (newest first, reversed to chronological)."""
    r = get_redis()
    key = _history_key(player_id)
    raw = await r.lrange(key, 0, count - 1)

    if not raw:
        # Fallback: load from PG
        pool = get_pg()
        rows = await pool.fetch(
            """SELECT role, content FROM conversation_messages
               WHERE player_id = $1 ORDER BY created_at DESC LIMIT $2""",
            uuid.UUID(player_id), count,
        )
        messages = [{"role": r["role"], "content": r["content"]} for r in rows]
        # Re-cache
        if messages:
            for msg in messages:
                await r.lpush(key, json.dumps(msg, ensure_ascii=False))
            await r.ltrim(key, 0, 49)
            await r.expire(key, 14400)
        return list(reversed(messages))

    messages = [json.loads(m) for m in raw]
    return list(reversed(messages))


async def get_summary(player_id: str) -> str | None:
    """Get conversation summary from Redis."""
    r = get_redis()
    return await r.get(_summary_key(player_id))


async def save_summary(player_id: str, summary: str) -> None:
    """Save conversation summary to Redis and PG."""
    r = get_redis()
    await r.set(_summary_key(player_id), summary, ex=14400)

    pool = get_pg()
    await pool.execute(
        """INSERT INTO conversation_summaries (player_id, summary)
           VALUES ($1, $2)""",
        uuid.UUID(player_id), summary,
    )
