"""NPC relationship service: manages player-NPC relationship levels.

Relationship levels affect:
  - NPC dialog tone/willingness to help
  - Available quests and services
  - Story branching outcomes

Scale: -100 (hostile) to 100 (devoted), default from npc_definitions.initial_relationship
"""

from __future__ import annotations

import logging
import uuid

from gameserver.config.settings import get_settings
from gameserver.db.postgres import get_pg

logger = logging.getLogger(__name__)


async def get_relationship(player_id: str, npc_id: str) -> dict:
    """Get relationship data for a player-NPC pair.

    Returns {"level": int, "interaction_count": int, "last_summary": str|None}
    Falls back to initial_relationship from npc_definitions if no row exists.
    """
    pool = get_pg()
    row = await pool.fetchrow(
        """SELECT relationship_level, interaction_count, last_interaction_summary
           FROM character_npc_relationships
           WHERE character_id = (
               SELECT id FROM player_characters WHERE player_id = $1
           ) AND npc_id = $2""",
        uuid.UUID(player_id), npc_id,
    )
    if row:
        return {
            "level": row["relationship_level"],
            "interaction_count": row["interaction_count"],
            "last_summary": row["last_interaction_summary"],
        }

    # Fallback: check npc_definitions for initial_relationship
    npc_def = await pool.fetchrow(
        "SELECT initial_relationship FROM npc_definitions WHERE id = $1", npc_id,
    )
    initial = npc_def["initial_relationship"] if npc_def else 0
    return {"level": initial, "interaction_count": 0, "last_summary": None}


async def get_all_relationships(player_id: str) -> list[dict]:
    """Get all NPC relationships for a player."""
    pool = get_pg()
    rows = await pool.fetch(
        """SELECT cnr.npc_id, cnr.relationship_level, cnr.interaction_count,
                  nd.name AS npc_name
           FROM character_npc_relationships cnr
           LEFT JOIN npc_definitions nd ON cnr.npc_id = nd.id
           WHERE cnr.character_id = (
               SELECT id FROM player_characters WHERE player_id = $1
           )
           ORDER BY cnr.relationship_level DESC""",
        uuid.UUID(player_id),
    )
    return [
        {
            "npc_id": r["npc_id"],
            "npc_name": r["npc_name"] or r["npc_id"],
            "level": r["relationship_level"],
            "interaction_count": r["interaction_count"],
        }
        for r in rows
    ]


async def update_relationship(
    player_id: str,
    npc_id: str,
    delta: int,
    interaction_summary: str | None = None,
) -> int:
    """Update NPC relationship level. Returns the new level.

    Clamps to [-100, 100] range.
    """
    pool = get_pg()
    char_id_row = await pool.fetchrow(
        "SELECT id FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    if not char_id_row:
        return 0

    char_id = char_id_row["id"]

    # Get initial_relationship as fallback for first interaction
    npc_def = await pool.fetchrow(
        "SELECT initial_relationship FROM npc_definitions WHERE id = $1", npc_id,
    )
    initial = npc_def["initial_relationship"] if npc_def else 0

    # Upsert with clamping
    rel_cfg = get_settings().game.relationship
    row = await pool.fetchrow(
        """INSERT INTO character_npc_relationships
           (character_id, npc_id, relationship_level, interaction_count, last_interaction_summary)
           VALUES ($1, $2, GREATEST($6, LEAST($7, $3::integer + $4::integer)), 1, $5)
           ON CONFLICT (character_id, npc_id)
           DO UPDATE SET
               relationship_level = GREATEST($6, LEAST($7,
                   character_npc_relationships.relationship_level + $4::integer)),
               interaction_count = character_npc_relationships.interaction_count + 1,
               last_interaction_summary = COALESCE($5, character_npc_relationships.last_interaction_summary)
           RETURNING relationship_level""",
        char_id, npc_id, initial, delta, interaction_summary,
        rel_cfg.min_level, rel_cfg.max_level,
    )

    new_level = row["relationship_level"] if row else initial + delta
    logger.debug(
        "NPC relationship: %s -> %s (%+d = %d) for player %s",
        npc_id, delta, new_level, new_level, player_id[:8],
    )
    return new_level


def get_relationship_tier(level: int) -> str:
    """Convert numeric relationship level to a descriptive tier."""
    tiers = get_settings().game.relationship.tiers
    for tier in tiers:
        if level >= tier.min:
            return tier.label
    return tiers[-1].label if tiers else "中立"
