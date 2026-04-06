"""Context builder: assembles 3-layer memory into LLM messages array.

Token budget (~4700 tokens/request):
  system prompt    ~800  (DM persona + world rules)
  tool definitions ~500  (ReAct tool schemas)
  player state     ~200  (compressed snapshot)
  summary          ~300  (adventure recap)
  RAG chunks       ~800  (ChromaDB retrieval)
  chat history     ~2000 (recent 10-15 turns)
  user input       ~100
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from gameserver.db import state_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位经验丰富的 DND 地下城主（Dungeon Master），负责主持一场基于《刀剑神域 Progressive》世界观的桌面角色扮演游戏。

## 世界设定
艾恩葛朗特（Aincrad）是一座漂浮在空中的巨大钢铁城堡，由 100 层楼组成。玩家（剑士）被困在其中，必须逐层攻略才能获得自由。死亡即真正的死亡——HP 归零意味着角色永久消失。

## 你的职责
1. **叙事**：用生动的文字描述场景、NPC 对话、战斗过程
2. **规则裁决**：严格遵循游戏系统规则，使用工具执行战斗/移动/交易等操作
3. **NPC 扮演**：赋予每个 NPC 独特的性格和说话方式
4. **冒险引导**：根据玩家位置和等级，自然地引入任务和事件

## 行为准则
- 永远不要替玩家做决定，提供选项让玩家自己选择
- 战斗时必须使用 attack 工具进行伤害计算，不要编造数值
- 保持 SAO 世界的紧张感——死亡是真实的
- 用「」标记 NPC 对话，用（）标记系统信息
- 回复控制在 200-400 字之间，除非是重大剧情场景"""


@dataclass
class GameContext:
    """Assembled context ready for LLM call."""
    messages: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)

    def add_tool_result(self, tool_call_id: str, result: dict) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": str(result),
        })


def _format_state_snapshot(state: dict) -> str:
    """Compress player state into a concise snapshot string."""
    if not state:
        return "[玩家状态] 未创建角色"

    name = state.get("name", "???")
    level = state.get("level", "1")
    hp = state.get("current_hp", "?")
    max_hp = state.get("max_hp", "?")
    col = state.get("col", "0")

    stats = (
        f"STR {state.get('stat_str', '10')} "
        f"AGI {state.get('stat_agi', '10')} "
        f"VIT {state.get('stat_vit', '10')} "
        f"INT {state.get('stat_int', '10')} "
        f"DEX {state.get('stat_dex', '10')} "
        f"LUK {state.get('stat_luk', '10')}"
    )

    floor = state.get("current_floor", "1")
    area = state.get("current_area", "起始之城")
    location = state.get("current_location", "中央广场")

    return (
        f"[玩家状态] {name} Lv.{level} | HP {hp}/{max_hp} | Col {col}\n"
        f"属性: {stats}\n"
        f"位置: 第{floor}层 {area} {location}"
    )


async def build_context(
    player_id: str,
    user_message: str,
    tools: list[dict],
    rag_chunks: list[str] | None = None,
) -> GameContext:
    """Build the full LLM context from 3-layer memory.

    Args:
        player_id: The authenticated player's UUID
        user_message: Current user input
        tools: OpenAI-format tool definitions for ReAct
        rag_chunks: Optional RAG retrieval results from ChromaDB
    """
    ctx = GameContext(tools=tools)

    # Layer 1: System prompt (DM persona + world rules)
    ctx.messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # Layer 2: Player state snapshot (from Redis/PG)
    state = await state_service.load_player_state(player_id)
    snapshot = _format_state_snapshot(state)
    ctx.messages.append({"role": "system", "content": snapshot})

    # Layer 3: Conversation summary (compressed old history)
    summary = await state_service.get_summary(player_id)
    if summary:
        ctx.messages.append({
            "role": "system",
            "content": f"[冒险经历摘要]\n{summary}",
        })

    # Layer 4: RAG retrieval results
    if rag_chunks:
        rag_text = "\n---\n".join(rag_chunks[:5])
        ctx.messages.append({
            "role": "system",
            "content": f"[世界知识参考]\n{rag_text}",
        })

    # Layer 5: Recent chat history (from Redis)
    history = await state_service.get_recent_messages(player_id, count=20)
    for msg in history:
        ctx.messages.append({"role": msg["role"], "content": msg["content"]})

    # Layer 6: Current user input
    ctx.messages.append({"role": "user", "content": user_message})

    return ctx


async def maybe_compress_history(player_id: str, llm_provider) -> None:
    """Check if history needs compression, and if so, generate summary.

    Trigger: Redis history > 40 messages
    Action: Summarize oldest 20 messages, trim to 30
    """
    from gameserver.db.redis_client import get_redis
    import json

    r = get_redis()
    key = state_service._history_key(player_id)
    length = await r.llen(key)

    if length <= 40:
        return

    logger.info("History compression triggered for %s (%d messages)", player_id, length)

    # Get oldest 20 messages (end of list since LPUSH puts newest first)
    oldest_raw = await r.lrange(key, 30, 49)
    if not oldest_raw:
        return

    oldest_msgs = [json.loads(m) for m in reversed(oldest_raw)]
    history_text = "\n".join(
        f"{'玩家' if m['role'] == 'user' else 'DM'}: {m['content'][:200]}"
        for m in oldest_msgs
    )

    # Generate summary via LLM
    summary_prompt = (
        "请用 150 字以内概括以下冒险经历的关键事件、地点变化和重要决策：\n\n"
        + history_text
    )
    try:
        new_summary = await llm_provider.chat([
            {"role": "system", "content": "你是一个简洁的摘要生成器。"},
            {"role": "user", "content": summary_prompt},
        ])
    except Exception as e:
        logger.error("Failed to generate summary: %s", e)
        return

    # Merge with existing summary
    existing = await state_service.get_summary(player_id)
    if existing:
        new_summary = f"{existing}\n\n{new_summary}"

    await state_service.save_summary(player_id, new_summary)

    # Trim Redis history to 30
    await r.ltrim(key, 0, 29)
    logger.info("History compressed for %s, summary updated", player_id)
