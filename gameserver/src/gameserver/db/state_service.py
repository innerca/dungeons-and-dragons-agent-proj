"""Player state service: Redis cache (Layer 2) with PG fallback (Layer 1)."""

from __future__ import annotations

import json
import logging
import time
import uuid

from gameserver.config.settings import get_settings
from gameserver.db.postgres import get_pg
from gameserver.db.redis_client import get_redis

logger = logging.getLogger(__name__)


# Redis key helpers
def _key_prefix() -> str:
    return get_settings().redis.key_prefix

def _state_key(pid: str) -> str:
    return f"{_key_prefix()}:player:{pid}:state"

def _history_key(pid: str) -> str:
    return f"{_key_prefix()}:player:{pid}:chat:history"

def _summary_key(pid: str) -> str:
    return f"{_key_prefix()}:player:{pid}:chat:summary"

def _auth_key(token: str) -> str:
    return f"{_key_prefix()}:auth:token:{token}"


async def store_auth_token(token: str, player_id: str) -> None:
    """Store auth token -> player_id mapping in Redis."""
    r = get_redis()
    ttl = get_settings().cache.auth_token_ttl
    await r.set(_auth_key(token), player_id, ex=ttl)


async def resolve_token(token: str) -> str | None:
    """Resolve auth token to player_id. Returns None if invalid/expired."""
    r = get_redis()
    return await r.get(_auth_key(token))


async def load_player_state(player_id: str, trace_id: str = "no-trace") -> dict:
    """Load player state from Redis, fallback to PG if cache miss.

    Returns a flat dict of character attributes.
    """
    start_time = time.time()
    r = get_redis()
    key = _state_key(player_id)

    # Try Redis first
    cached = await r.hgetall(key)
    if cached:
        latency_ms = (time.time() - start_time) * 1000
        logger.debug("trace=%s step=state_load source=redis fields=%d latency_ms=%.1f", trace_id, len(cached), latency_ms)
        return cached

    # Fallback to PG
    logger.debug("trace=%s step=state_load source=redis status=miss", trace_id)
    pg_start = time.time()
    pool = get_pg()
    row = await pool.fetchrow(
        "SELECT * FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    pg_latency_ms = (time.time() - pg_start) * 1000
    if not row:
        logger.debug("trace=%s step=state_load source=postgres status=not_found latency_ms=%.1f", trace_id, pg_latency_ms)
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
        "stat_points_available": str(row.get("stat_points_available", 0) or 0),
    }

    # Cache to Redis
    state_ttl = get_settings().cache.state_ttl
    await r.hset(key, mapping=state)
    await r.expire(key, state_ttl)
    
    total_latency_ms = (time.time() - start_time) * 1000
    logger.debug("trace=%s step=state_load source=postgres fields=%d pg_ms=%.1f total_ms=%.1f", trace_id, len(state), pg_latency_ms, total_latency_ms)

    return state


async def save_player_state(player_id: str, changes: dict, trace_id: str = "no-trace") -> None:
    """Write-Through: update Redis immediately, async persist to PG."""
    start_time = time.time()
    r = get_redis()
    key = _state_key(player_id)
    state_ttl = get_settings().cache.state_ttl

    # Update Redis
    if changes:
        await r.hset(key, mapping={k: str(v) for k, v in changes.items()})
        await r.expire(key, state_ttl)
        logger.debug("trace=%s step=state_save target=redis fields=%d", trace_id, len(changes))

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
        "stat_points_available": "stat_points_available",
        "stat_str": "stat_str",
        "stat_agi": "stat_agi",
        "stat_vit": "stat_vit",
        "stat_int": "stat_int",
        "stat_dex": "stat_dex",
        "stat_luk": "stat_luk",
    }
    str_fields = ("current_area", "current_location")
    for k, v in changes.items():
        if k in field_map:
            pg_updates[field_map[k]] = v if k in str_fields else int(v)

    if pg_updates:
        pg_start = time.time()
        pool = get_pg()
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(pg_updates))
        query = f"UPDATE player_characters SET {sets}, updated_at = now() WHERE player_id = $1"
        await pool.execute(query, uuid.UUID(player_id), *pg_updates.values())
        pg_latency_ms = (time.time() - pg_start) * 1000
        total_latency_ms = (time.time() - start_time) * 1000
        logger.debug("trace=%s step=state_save target=postgres fields=%d pg_ms=%.1f total_ms=%.1f", trace_id, len(pg_updates), pg_latency_ms, total_latency_ms)


# --- Conversation History (Redis Layer) ---

async def push_message(player_id: str, role: str, content: str) -> int:
    """Push a message to Redis chat history. Returns current length."""
    r = get_redis()
    cache_cfg = get_settings().cache
    key = _history_key(player_id)
    msg = json.dumps({"role": role, "content": content}, ensure_ascii=False)
    await r.lpush(key, msg)
    await r.ltrim(key, 0, cache_cfg.max_stored_messages - 1)
    await r.expire(key, cache_cfg.history_ttl)
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
    cache_cfg = get_settings().cache
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
            await r.ltrim(key, 0, cache_cfg.max_stored_messages - 1)
            await r.expire(key, cache_cfg.history_ttl)
        return list(reversed(messages))

    messages = [json.loads(m) for m in raw]
    return list(reversed(messages))


async def get_summary(player_id: str) -> str | None:
    """Get conversation summary from Redis, fallback to PG."""
    r = get_redis()
    summary_ttl = get_settings().cache.summary_ttl
    cached = await r.get(_summary_key(player_id))
    if cached:
        return cached

    # PG fallback
    pool = get_pg()
    row = await pool.fetchrow(
        """SELECT summary FROM conversation_summaries
           WHERE player_id = $1 ORDER BY created_at DESC LIMIT 1""",
        uuid.UUID(player_id),
    )
    if row:
        await r.set(_summary_key(player_id), row["summary"], ex=summary_ttl)
        return row["summary"]
    return None


async def save_summary(player_id: str, summary: str) -> None:
    """Save conversation summary to Redis and PG."""
    r = get_redis()
    summary_ttl = get_settings().cache.summary_ttl
    await r.set(_summary_key(player_id), summary, ex=summary_ttl)

    pool = get_pg()
    await pool.execute(
        """INSERT INTO conversation_summaries (player_id, summary)
           VALUES ($1, $2)""",
        uuid.UUID(player_id), summary,
    )
