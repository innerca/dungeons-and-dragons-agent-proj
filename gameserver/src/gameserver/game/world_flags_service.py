"""World flags service: manages story/progression flags per character.

Flags are key-value pairs stored in character_world_flags.
Used for:
  - Story branching (e.g. floor1_cleared, anneal_blade_obtained)
  - Quest prerequisites (required_flags in quest_definitions)
  - NPC dialog gating (e.g. argo_contact enables info purchases)
"""

from __future__ import annotations

import logging
import uuid

from gameserver.db.postgres import get_pg

logger = logging.getLogger(__name__)


async def get_flag(player_id: str, flag_key: str) -> str | None:
    """Get a single world flag value, or None if not set."""
    pool = get_pg()
    row = await pool.fetchrow(
        """SELECT flag_value FROM character_world_flags
           WHERE character_id = (
               SELECT id FROM player_characters WHERE player_id = $1
           ) AND flag_key = $2""",
        uuid.UUID(player_id), flag_key,
    )
    return row["flag_value"] if row else None


async def get_all_flags(player_id: str) -> dict[str, str]:
    """Get all world flags for a player as a dict."""
    pool = get_pg()
    rows = await pool.fetch(
        """SELECT flag_key, flag_value FROM character_world_flags
           WHERE character_id = (
               SELECT id FROM player_characters WHERE player_id = $1
           )""",
        uuid.UUID(player_id),
    )
    return {r["flag_key"]: r["flag_value"] for r in rows}


async def set_flag(player_id: str, flag_key: str, flag_value: str) -> None:
    """Set (upsert) a world flag."""
    pool = get_pg()
    char_id_row = await pool.fetchrow(
        "SELECT id FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    if not char_id_row:
        return

    await pool.execute(
        """INSERT INTO character_world_flags (character_id, flag_key, flag_value)
           VALUES ($1, $2, $3)
           ON CONFLICT (character_id, flag_key)
           DO UPDATE SET flag_value = $3, set_at = now()""",
        char_id_row["id"], flag_key, flag_value,
    )
    logger.debug("Flag set: %s = %s for player %s", flag_key, flag_value, player_id[:8])


async def check_flag(player_id: str, flag_key: str, expected: str = "true") -> bool:
    """Check if a flag matches the expected value."""
    val = await get_flag(player_id, flag_key)
    return val == expected
