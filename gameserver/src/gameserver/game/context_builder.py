"""Context builder: assembles 3-layer memory into LLM messages array.

Token budget (~4700 tokens/request):
  system prompt    ~800  (DM persona + world rules)
  tool definitions ~500  (ReAct tool schemas)
  player state     ~200  (compressed snapshot)
  quest/npc info   ~200  (active quests + key relationships)
  combat state     ~100  (current combat if any)
  summary          ~300  (adventure recap)
  RAG chunks       ~800  (ChromaDB retrieval)
  chat history     ~2000 (recent 10-15 turns)
  user input       ~100
"""

from __future__ import annotations

import json
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

FIRST_MESSAGE_GUIDE = """## 新玩家欢迎引导

这是玩家的第一次冒险。请以游戏大师（DM）的身份生成一段 200-300 字的欢迎词，必须包含：

1. **世界观简介**（3-4句）：你们被困在浮游城堡艾恩葛朗特，死亡意味着真正的消亡，唯一的出路是逐层攻略到第100层。
2. **初始行动建议**：
   - 先在起始之城周围的草原狩猎山猪、野狼积累经验和珂尔
   - 等级提升后前往北方的托尔巴纳镇，那里有铁匠和任务NPC
   - 可以使用「查看状态」查看属性，「查看背包」查看道具
3. **安全提醒**：城镇内有防犯罪指令保护，离开城镇就要自负安全
4. **鼓励冒险**：以热情但带紧张感的语气邀请玩家做出第一个选择

语气要求：像一位经验丰富的前辈剑士在向新手介绍这个世界，兼具热情与严肃。不要使用markdown格式，用自然的叙事语气。"""


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


async def _format_quest_snapshot(player_id: str) -> str | None:
    """Format active quests into a concise context block."""
    try:
        from gameserver.game.quest_service import get_active_quests
        quests = await get_active_quests(player_id)
    except Exception:
        return None

    if not quests:
        return None

    lines = ["[活跃任务]"]
    for q in quests[:5]:
        status_icon = "!" if q["status"] == "available" else ">"
        line = f"  {status_icon} {q['name']}({q['quest_type']}) [{q['status']}]"

        if q["status"] == "active" and q.get("progress"):
            progress = q["progress"]
            objectives = q.get("objectives", [])
            done = sum(1 for k, v in progress.items() if v.get("completed"))
            total = len(objectives)
            if total > 0:
                line += f" ({done}/{total})"
        lines.append(line)

    return "\n".join(lines)


async def _format_combat_snapshot(player_id: str) -> str | None:
    """Format active combat state into context."""
    try:
        from gameserver.game.combat_state import get_combat
        session = await get_combat(player_id)
    except Exception:
        return None

    if not session:
        return None

    m = session.monster
    return (
        f"[战斗中] vs {m.name} — HP {m.hp}/{m.max_hp} | "
        f"ATK {m.atk} DEF {m.defense} AC {m.ac} | 回合 {session.round_number}"
    )


async def _format_relationship_snapshot(player_id: str) -> str | None:
    """Format key NPC relationships into context."""
    try:
        from gameserver.game.npc_relationship_service import get_all_relationships, get_relationship_tier
        rels = await get_all_relationships(player_id)
    except Exception:
        return None

    if not rels:
        return None

    active_rels = [r for r in rels if r["interaction_count"] > 0]
    if not active_rels:
        return None

    lines = ["[NPC关系]"]
    for r in active_rels[:6]:
        tier = get_relationship_tier(r["level"])
        lines.append(f"  {r['npc_name']}: {tier}({r['level']:+d})")

    return "\n".join(lines)


async def build_context(
    player_id: str,
    user_message: str,
    tools: list[dict],
    rag_chunks: list[str] | None = None,
    trace_id: str = "no-trace",
    is_first_message: bool = False,
) -> GameContext:
    """Build the full LLM context from 3-layer memory.

    Args:
        player_id: The authenticated player's UUID
        user_message: Current user input
        tools: OpenAI-format tool definitions for ReAct
        rag_chunks: Optional RAG retrieval results from ChromaDB
        trace_id: Trace ID for logging
        is_first_message: Whether this is the player's first message
    """
    import time
    start_time = time.time()

    ctx = GameContext(tools=tools)

    # Layer 1: System prompt (DM persona + world rules)
    ctx.messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # Layer 1.5: First message guide for new players
    if is_first_message:
        ctx.messages.append({"role": "system", "content": FIRST_MESSAGE_GUIDE})
    system_tokens = len(SYSTEM_PROMPT) // 4  # Rough estimate: 4 chars per token

    # Layer 2: Player state snapshot (from Redis/PG)
    state = await state_service.load_player_state(player_id, trace_id=trace_id)
    snapshot = _format_state_snapshot(state)

    # Append combat state, active quests, and NPC relationships to snapshot
    combat_snap = await _format_combat_snapshot(player_id)
    quest_snap = await _format_quest_snapshot(player_id)
    rel_snap = await _format_relationship_snapshot(player_id)

    enriched = snapshot
    snapshot_tokens = len(enriched) // 4
    if combat_snap:
        enriched += f"\n{combat_snap}"
    if quest_snap:
        enriched += f"\n{quest_snap}"
    if rel_snap:
        enriched += f"\n{rel_snap}"

    ctx.messages.append({"role": "system", "content": enriched})
    context_tokens = len(enriched) // 4 - snapshot_tokens

    # Layer 3: Conversation summary (compressed old history)
    summary = await state_service.get_summary(player_id)
    summary_tokens = 0
    if summary:
        summary_tokens = len(summary) // 4
        ctx.messages.append({
            "role": "system",
            "content": f"[冒险经历摘要]\n{summary}",
        })

    # Layer 4: RAG retrieval results
    rag_tokens = 0
    if rag_chunks:
        rag_text = "\n---\n".join(rag_chunks[:5])
        rag_tokens = len(rag_text) // 4
        ctx.messages.append({
            "role": "system",
            "content": f"[世界知识参考]\n{rag_text}",
        })

    # Layer 5: Recent chat history (from Redis)
    history = await state_service.get_recent_messages(player_id, count=20)
    history_tokens = 0
    for msg in history:
        ctx.messages.append({"role": msg["role"], "content": msg["content"]})
        history_tokens += len(msg.get("content", "")) // 4

    # Layer 6: Current user input
    ctx.messages.append({"role": "user", "content": user_message})
    user_tokens = len(user_message) // 4
    
    # Log context assembly stats
    total_tokens = system_tokens + context_tokens + summary_tokens + rag_tokens + history_tokens + user_tokens
    latency_ms = (time.time() - start_time) * 1000
    logger.debug(
        "trace=%s step=context_build latency_ms=%.1f tokens_est=%d (system=%d context=%d summary=%d rag=%d history=%d user=%d)",
        trace_id, latency_ms, total_tokens, system_tokens, context_tokens, summary_tokens, rag_tokens, history_tokens, user_tokens
    )

    return ctx


async def maybe_compress_history(player_id: str, llm_provider, trace_id: str = "no-trace") -> None:
    """Check if history needs compression, and if so, generate summary.

    Trigger: Redis history > 40 messages
    Action: Summarize oldest 20 messages, trim to 30
    """
    from gameserver.db.redis_client import get_redis
    import json
    import time

    r = get_redis()
    key = state_service._history_key(player_id)
    length = await r.llen(key)

    if length <= 40:
        logger.debug("trace=%s step=history_compress status=skip messages=%d", trace_id, length)
        return

    logger.info("trace=%s step=history_compress status=triggered messages=%d", trace_id, length)

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
    logger.info("trace=%s step=history_compress status=complete messages=%d->30", trace_id, length)
