"""Quest state machine: manages quest lifecycle and progress tracking.

Quest FSM:
  [no row]     undiscovered - player hasn't encountered the quest
  "available"  trigger fired, prerequisites met, can be accepted
  "active"     accepted, objectives being tracked
  "completed"  all objectives done, rewards granted
  "failed"     quest failed

Trigger types (from quest_definitions.trigger_json):
  - location:  fires when player moves to a matching area
  - npc_talk:  fires when player talks to a specific NPC
  - item:      fires when player obtains a specific item
  - auto:      fires immediately when prerequisites are met

Integration points:
  - check_quest_triggers() is called after every action execution
  - update_quest_progress() is called for kill/collect/talk/reach events
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from gameserver.db.postgres import get_pg

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Query helpers
# ------------------------------------------------------------------

async def get_active_quests(player_id: str) -> list[dict]:
    """Return all active quests for a player, joined with quest_definitions."""
    pool = get_pg()
    rows = await pool.fetch(
        """SELECT cq.quest_def_id, cq.status, cq.progress_json,
                  qd.name, qd.quest_type, qd.objectives_json, qd.description
           FROM character_quests cq
           JOIN quest_definitions qd ON cq.quest_def_id = qd.id
           WHERE cq.character_id = (
               SELECT id FROM player_characters WHERE player_id = $1
           )
           AND cq.status IN ('active', 'available')
           ORDER BY cq.started_at""",
        uuid.UUID(player_id),
    )
    result = []
    for r in rows:
        progress = r["progress_json"] or {}
        if isinstance(progress, str):
            progress = json.loads(progress)
        objectives = r["objectives_json"] or []
        if isinstance(objectives, str):
            objectives = json.loads(objectives)
        result.append({
            "quest_id": r["quest_def_id"],
            "name": r["name"],
            "quest_type": r["quest_type"],
            "status": r["status"],
            "objectives": objectives,
            "progress": progress,
            "description": r["description"],
        })
    return result


async def get_quest_status(player_id: str, quest_def_id: str) -> str | None:
    """Return the status of a specific quest, or None if undiscovered."""
    pool = get_pg()
    row = await pool.fetchrow(
        """SELECT cq.status FROM character_quests cq
           WHERE cq.character_id = (
               SELECT id FROM player_characters WHERE player_id = $1
           ) AND cq.quest_def_id = $2""",
        uuid.UUID(player_id), quest_def_id,
    )
    return row["status"] if row else None


# ------------------------------------------------------------------
# Prerequisite checking
# ------------------------------------------------------------------

async def _check_prerequisites(
    player_id: str, state: dict, prereqs: dict
) -> bool:
    """Check if a player meets quest prerequisites."""
    if not prereqs:
        return True

    # Level check
    min_level = prereqs.get("min_level")
    if min_level and int(state.get("level", 1)) < int(min_level):
        return False

    # Required quests completed
    required_quests = prereqs.get("required_quests", [])
    if required_quests:
        pool = get_pg()
        for qid in required_quests:
            status = await get_quest_status(player_id, qid)
            if status != "completed":
                return False

    # Required world flags
    required_flags = prereqs.get("required_flags", {})
    if required_flags:
        if not isinstance(required_flags, dict):
            logger.warning("Invalid required_flags format for player %s: %s", player_id[:8], required_flags)
            return False
        pool = get_pg()
        for flag_key, expected in required_flags.items():
            row = await pool.fetchrow(
                """SELECT flag_value FROM character_world_flags
                   WHERE character_id = (
                       SELECT id FROM player_characters WHERE player_id = $1
                   ) AND flag_key = $2""",
                uuid.UUID(player_id), flag_key,
            )
            if not row or row["flag_value"] != str(expected):
                return False

    return True


# ------------------------------------------------------------------
# Trigger checking (post-action hook)
# ------------------------------------------------------------------

async def check_quest_triggers(
    player_id: str,
    state: dict,
    trigger_type: str,
    trigger_target: str,
) -> list[str]:
    """Check if any undiscovered quests should become available.

    Called after actions that could trigger quests:
      - move_to      -> trigger_type="location", trigger_target=area
      - talk_to_npc  -> trigger_type="npc_talk", trigger_target=npc_id
      - use_item     -> trigger_type="item", trigger_target=item_id

    Returns list of quest names that were newly triggered.
    """
    pool = get_pg()
    current_floor = int(state.get("current_floor", 1))

    # Find quest definitions for current floor with matching trigger type
    quest_defs = await pool.fetch(
        """SELECT id, name, prerequisites_json, trigger_json
           FROM quest_definitions
           WHERE floor <= $1""",
        current_floor,
    )

    newly_available: list[str] = []

    for qdef in quest_defs:
        quest_id = qdef["id"]

        # Skip if player already has this quest
        existing_status = await get_quest_status(player_id, quest_id)
        if existing_status is not None:
            continue

        # Parse trigger
        trigger = qdef["trigger_json"] or {}
        if isinstance(trigger, str):
            trigger = json.loads(trigger)

        t_type = trigger.get("type", "")
        t_target = trigger.get("target", "")

        # Check if this trigger matches the current action
        match = False
        if t_type == trigger_type:
            if trigger_type == "location":
                # Fuzzy match: area name contains target or vice versa
                match = t_target in trigger_target or trigger_target in t_target
            elif trigger_type == "npc_talk":
                match = t_target == trigger_target
            elif trigger_type == "item":
                match = t_target == trigger_target
        elif t_type == "auto":
            match = True  # Auto-trigger always fires when prereqs are met

        if not match:
            continue

        # Check prerequisites
        prereqs = qdef["prerequisites_json"] or {}
        if isinstance(prereqs, str):
            prereqs = json.loads(prereqs)

        if not await _check_prerequisites(player_id, state, prereqs):
            continue

        # Create quest entry as "available"
        char_id = state.get("character_id")
        if not char_id:
            continue

        await pool.execute(
            """INSERT INTO character_quests (character_id, quest_def_id, status, progress_json)
               VALUES ($1, $2, 'available', '{}')
               ON CONFLICT DO NOTHING""",
            uuid.UUID(char_id), quest_id,
        )
        newly_available.append(qdef["name"])
        logger.info("Quest available: %s for player %s", quest_id, player_id[:8])

    return newly_available


# ------------------------------------------------------------------
# Quest acceptance
# ------------------------------------------------------------------

async def accept_quest(player_id: str, quest_def_id: str) -> dict:
    """Accept an available quest, initialize progress tracking.

    Returns {"success": bool, "message": str, "quest_name": str}
    """
    pool = get_pg()
    char_id_row = await pool.fetchrow(
        "SELECT id FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    if not char_id_row:
        return {"success": False, "message": "未创建角色", "quest_name": ""}

    char_id = char_id_row["id"]

    # Check current status
    row = await pool.fetchrow(
        """SELECT cq.status, qd.name, qd.objectives_json
           FROM character_quests cq
           JOIN quest_definitions qd ON cq.quest_def_id = qd.id
           WHERE cq.character_id = $1 AND cq.quest_def_id = $2""",
        char_id, quest_def_id,
    )

    if not row:
        return {"success": False, "message": f"任务 {quest_def_id} 未解锁", "quest_name": ""}

    if row["status"] == "active":
        return {"success": False, "message": f"任务「{row['name']}」已在进行中", "quest_name": row["name"]}

    if row["status"] == "completed":
        return {"success": False, "message": f"任务「{row['name']}」已完成", "quest_name": row["name"]}

    if row["status"] != "available":
        return {"success": False, "message": f"任务状态异常: {row['status']}", "quest_name": row["name"]}

    # Initialize progress from objectives
    objectives = row["objectives_json"] or []
    if isinstance(objectives, str):
        objectives = json.loads(objectives)

    progress = {}
    for i, obj in enumerate(objectives):
        progress[f"obj_{i}"] = {
            "type": obj.get("type", "unknown"),
            "target": obj.get("target", ""),
            "required": obj.get("count", 1),
            "current": 0,
            "completed": False,
        }

    await pool.execute(
        """UPDATE character_quests
           SET status = 'active', progress_json = $1, started_at = now()
           WHERE character_id = $2 AND quest_def_id = $3""",
        json.dumps(progress, ensure_ascii=False),
        char_id, quest_def_id,
    )

    logger.info("Quest accepted: %s by player %s", quest_def_id, player_id[:8])
    return {"success": True, "message": f"接受任务「{row['name']}」", "quest_name": row["name"]}


# ------------------------------------------------------------------
# Progress update (called after relevant actions)
# ------------------------------------------------------------------

async def update_quest_progress(
    player_id: str,
    event_type: str,
    event_target: str,
    count: int = 1,
) -> list[str]:
    """Update progress for all active quests matching the event.

    event_type: "kill" | "collect" | "talk" | "reach"
    event_target: monster_id / item_id / npc_id / area_name

    Returns list of notification messages (progress updates, completions).
    """
    pool = get_pg()
    char_id_row = await pool.fetchrow(
        "SELECT id FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    if not char_id_row:
        return []

    char_id = char_id_row["id"]

    # Get all active quests
    rows = await pool.fetch(
        """SELECT cq.id, cq.quest_def_id, cq.progress_json,
                  qd.name, qd.objectives_json, qd.rewards_json
           FROM character_quests cq
           JOIN quest_definitions qd ON cq.quest_def_id = qd.id
           WHERE cq.character_id = $1 AND cq.status = 'active'""",
        char_id,
    )

    messages: list[str] = []

    for quest_row in rows:
        progress = quest_row["progress_json"] or {}
        if isinstance(progress, str):
            progress = json.loads(progress)

        objectives = quest_row["objectives_json"] or []
        if isinstance(objectives, str):
            objectives = json.loads(objectives)

        updated = False
        for i, obj in enumerate(objectives):
            key = f"obj_{i}"
            if key not in progress:
                continue

            p = progress[key]
            if p.get("completed"):
                continue

            # Match event to objective
            if obj.get("type") != event_type:
                continue

            obj_target = obj.get("target", "")
            # Flexible matching: exact match or containment
            if event_type == "reach":
                if obj_target not in event_target and event_target not in obj_target:
                    continue
            else:
                if obj_target != event_target:
                    continue

            # Update count
            p["current"] = p.get("current", 0) + count
            if p["current"] >= p.get("required", 1):
                p["current"] = p["required"]
                p["completed"] = True
                messages.append(
                    f"[任务进度] 「{quest_row['name']}」目标完成: {obj.get('desc', obj_target)}"
                )
            else:
                messages.append(
                    f"[任务进度] 「{quest_row['name']}」: {obj.get('desc', obj_target)} "
                    f"({p['current']}/{p['required']})"
                )
            progress[key] = p
            updated = True

        if not updated:
            continue

        # Save updated progress
        await pool.execute(
            """UPDATE character_quests SET progress_json = $1
               WHERE id = $2""",
            json.dumps(progress, ensure_ascii=False),
            quest_row["id"],
        )

        # Check if all objectives completed
        all_done = all(
            progress.get(f"obj_{i}", {}).get("completed", False)
            for i in range(len(objectives))
        )
        if all_done:
            completion_msg = await _complete_quest(
                player_id, char_id, quest_row["quest_def_id"],
                quest_row["name"], quest_row["rewards_json"],
            )
            messages.append(completion_msg)

    return messages


# ------------------------------------------------------------------
# Quest completion & reward granting
# ------------------------------------------------------------------

async def _complete_quest(
    player_id: str,
    char_id: Any,
    quest_def_id: str,
    quest_name: str,
    rewards_json: Any,
) -> str:
    """Mark quest completed and grant rewards.

    Returns a completion message string.
    """
    pool = get_pg()

    # Parse rewards
    rewards = rewards_json or {}
    if isinstance(rewards, str):
        rewards = json.loads(rewards)

    # Mark completed
    await pool.execute(
        """UPDATE character_quests
           SET status = 'completed', completed_at = now()
           WHERE character_id = $1 AND quest_def_id = $2""",
        char_id, quest_def_id,
    )

    parts = [f"任务「{quest_name}」完成！"]

    # Grant EXP
    exp_reward = rewards.get("exp", 0)
    if exp_reward:
        await pool.execute(
            """UPDATE player_characters
               SET experience = experience + $1
               WHERE id = $2""",
            exp_reward, char_id,
        )
        parts.append(f"获得 {exp_reward} 经验值")

    # Grant Col
    col_reward = rewards.get("col", 0)
    if col_reward:
        await pool.execute(
            """UPDATE player_characters SET col = col + $1 WHERE id = $2""",
            col_reward, char_id,
        )
        parts.append(f"获得 {col_reward} 珂尔")

    # Grant items
    item_ids = rewards.get("items", [])
    granted_items = []
    for item_id in item_ids:
        item_def = await pool.fetchrow(
            "SELECT name, weapon_durability FROM item_definitions WHERE id = $1",
            item_id,
        )
        if item_def:
            await pool.execute(
                """INSERT INTO character_inventory
                   (character_id, item_def_id, quantity, current_durability)
                   VALUES ($1, $2, 1, $3)""",
                char_id, item_id, item_def["weapon_durability"],
            )
            granted_items.append(item_def["name"])
    if granted_items:
        parts.append(f"获得物品: {', '.join(granted_items)}")

    # Set world flags
    flags = rewards.get("flags", {})
    for flag_key, flag_value in flags.items():
        await pool.execute(
            """INSERT INTO character_world_flags (character_id, flag_key, flag_value)
               VALUES ($1, $2, $3)
               ON CONFLICT (character_id, flag_key) DO UPDATE SET flag_value = $3, set_at = now()""",
            char_id, flag_key, str(flag_value),
        )

    # Update NPC relationships
    relationships = rewards.get("relationships", {})
    for npc_id, delta in relationships.items():
        await pool.execute(
            """INSERT INTO character_npc_relationships
               (character_id, npc_id, relationship_level, interaction_count)
               VALUES ($1, $2, $3, 1)
               ON CONFLICT (character_id, npc_id)
               DO UPDATE SET relationship_level = character_npc_relationships.relationship_level + $3,
                             interaction_count = character_npc_relationships.interaction_count + 1""",
            char_id, npc_id, int(delta),
        )

    # Sync state to Redis (exp, col changes)
    from gameserver.db import state_service
    state_changes = {}
    if exp_reward:
        state_changes["experience"] = exp_reward  # delta - will need fresh load
    if col_reward:
        state_changes["col"] = col_reward

    # Force a fresh state reload by invalidating Redis cache
    from gameserver.db.redis_client import get_redis
    r = get_redis()
    await r.delete(f"sao:player:{player_id}:state")

    logger.info("Quest completed: %s by player %s", quest_def_id, player_id[:8])
    return "。".join(parts)
