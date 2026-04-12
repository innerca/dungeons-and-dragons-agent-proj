"""Scene classifier for dynamic context pruning.

Detects scene type from player message to optimize token usage:
  - combat: Only include combat tools + monster RAG
  - exploration: Only include movement tools + area RAG
  - social: Only include interaction tools + NPC RAG
  - rest: Minimal tools
  - general: All tools (default fallback)

Saves ~150-200 tokens by pruning irrelevant tool definitions per request.
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class SceneType(Enum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    REST = "rest"
    GENERAL = "general"


# Tool names grouped by scene relevance
TOOL_GROUPS: dict[SceneType, set[str]] = {
    SceneType.COMBAT: {
        "attack", "defend", "use_item", "flee",
        "check_status", "check_inventory", "roll_dice",
    },
    SceneType.EXPLORATION: {
        "move_to", "enter_dungeon", "use_teleport_crystal",
        "inspect", "check_status", "check_inventory", "roll_dice",
    },
    SceneType.SOCIAL: {
        "talk_to_npc", "trade", "accept_quest", "inspect",
        "check_status", "check_inventory",
    },
    SceneType.REST: {
        "rest", "use_item", "check_status", "check_inventory",
        "equip_item",
    },
}

# Default: all tools (no pruning)
_ALL_TOOL_NAMES: set[str] | None = None


def classify_scene(
    message: str,
    scene_keywords: dict[str, list[str]] | None = None,
    trace_id: str = "no-trace",
) -> SceneType:
    """Classify the player's message into a scene type.

    Args:
        message: The player's input message
        scene_keywords: Optional keyword mapping from game config.
            Format: {"combat": ["攻击", "战斗", ...], "social": [...], ...}
        trace_id: Trace ID for logging

    Returns:
        The detected SceneType
    """
    if not scene_keywords:
        # Fallback defaults
        scene_keywords = {
            "combat": ["攻击", "战斗", "剑技", "防御", "逃跑", "怪物", "BOSS", "HP"],
            "exploration": ["移动", "前往", "探索", "进入", "走", "迷宫"],
            "social": ["对话", "说", "问", "NPC", "购买", "出售", "交易", "情报"],
            "rest": ["休息", "回复", "旅馆", "睡觉"],
        }

    scores: dict[str, int] = {}
    msg_lower = message.lower()
    msg_preview = message[:50] + "..." if len(message) > 50 else message

    for scene_name, keywords in scene_keywords.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            scores[scene_name] = score

    if not scores:
        logger.debug("trace=%s step=scene_classify input='%s' result=general", trace_id, msg_preview)
        return SceneType.GENERAL

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    try:
        scene_type = SceneType(best)
        logger.debug("trace=%s step=scene_classify input='%s' result=%s scores=%s", trace_id, msg_preview, best, scores)
        return scene_type
    except ValueError:
        logger.debug("trace=%s step=scene_classify input='%s' result=general error=invalid_scene", trace_id, msg_preview)
        return SceneType.GENERAL


def prune_tools(
    tools: list[dict],
    scene: SceneType,
) -> list[dict]:
    """Filter tool definitions based on scene type.

    Args:
        tools: Full list of OpenAI-format tool definitions
        scene: The detected scene type

    Returns:
        Filtered tool list (or full list for GENERAL)
    """
    if scene == SceneType.GENERAL:
        return tools

    allowed = TOOL_GROUPS.get(scene)
    if not allowed:
        return tools

    pruned = [
        t for t in tools
        if t.get("function", {}).get("name") in allowed
    ]

    logger.debug(
        "Pruned tools: %d -> %d (scene=%s)",
        len(tools), len(pruned), scene.value,
    )
    return pruned


def get_rag_entity_type(scene: SceneType) -> str | None:
    """Get the preferred entity type filter for RAG queries.

    Returns:
        Entity type string for ChromaDB filtering, or None for unfiltered.
    """
    mapping = {
        SceneType.COMBAT: "monster",
        SceneType.SOCIAL: "npc",
        SceneType.EXPLORATION: None,  # mixed - areas + quests
        SceneType.REST: None,
        SceneType.GENERAL: None,
    }
    return mapping.get(scene)
