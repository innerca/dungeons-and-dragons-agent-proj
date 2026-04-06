"""Action Executor: 5-step validation chain for ReAct tool calls.

Step 1: Permission check
Step 2: Precondition validation
Step 3: Resource check
Step 4: Deterministic computation (dice + formulas)
Step 5: State write (Redis → async PG)
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from dataclasses import dataclass, field

from gameserver.db.postgres import get_pg
from gameserver.db import state_service
from gameserver.game.combat_state import (
    get_combat, start_combat, update_combat, end_combat,
    calculate_counter_attack, CombatSession,
)
from gameserver.game import quest_service
from gameserver.game import npc_relationship_service

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    success: bool
    action_type: str = ""
    description: str = ""
    error: str = ""
    state_changes: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)

    def to_tool_result(self) -> str:
        if not self.success:
            return json.dumps({"success": False, "error": self.error}, ensure_ascii=False)
        result = {"success": True, "description": self.description}
        result.update(self.details)
        return json.dumps(result, ensure_ascii=False)


def _roll(sides: int = 20, count: int = 1, modifier: int = 0) -> dict:
    """Core dice roller."""
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    return {
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "natural_max": any(r == sides for r in rolls),
        "natural_1": any(r == 1 for r in rolls),
    }


def _stat_mod(stat_value: int) -> int:
    """Convert stat to modifier: (stat - 10) // 2."""
    return (int(stat_value) - 10) // 2


def _calc_exp_to_next(level: int) -> int:
    """exp_to_next = 100 * level^1.5"""
    return int(100 * level ** 1.5)


def _calc_max_hp(level: int, vit: int) -> int:
    """max_hp = 200 + level*50 + vit*10"""
    return 200 + level * 50 + vit * 10


async def _check_level_up(player_id: str, state: dict, state_changes: dict) -> str:
    """Check if player should level up after gaining EXP.

    Modifies state_changes in place. Returns level-up description or empty string.
    """
    exp = state_changes.get("experience", int(state.get("experience", 0)))
    level = int(state.get("level", 1))
    exp_to_next = int(state.get("exp_to_next", _calc_exp_to_next(level)))
    vit = int(state.get("stat_vit", 10))

    level_ups = 0
    while exp >= exp_to_next:
        exp -= exp_to_next
        level += 1
        level_ups += 1
        exp_to_next = _calc_exp_to_next(level)

    if level_ups == 0:
        return ""

    new_max_hp = _calc_max_hp(level, vit)
    stat_pts = int(state.get("stat_points_available", 0)) + level_ups * 3

    state_changes["level"] = level
    state_changes["experience"] = exp
    state_changes["exp_to_next"] = exp_to_next
    state_changes["max_hp"] = new_max_hp
    state_changes["current_hp"] = new_max_hp  # Full heal on level up
    state_changes["stat_points_available"] = stat_pts

    await state_service.save_player_state(player_id, state_changes)

    return (
        f"\nレベルアップ！Lv.{level - level_ups} → Lv.{level}！"
        f"HP全回復（{new_max_hp}）、自由分配点数+{level_ups * 3}（合計{stat_pts}）。"
    )


class ActionExecutor:
    """Executes tool calls with 5-step validation."""

    async def execute(
        self, player_id: str, state: dict, tool_name: str, tool_args: dict
    ) -> ActionResult:
        handler = getattr(self, f"_handle_{tool_name}", None)
        if handler is None:
            return ActionResult(
                success=False,
                action_type=tool_name,
                error=f"Unknown tool: {tool_name}",
            )

        try:
            return await handler(player_id, state, tool_args)
        except Exception as e:
            logger.error("Action execution error: %s", e, exc_info=True)
            return ActionResult(
                success=False, action_type=tool_name, error=f"执行错误: {str(e)}"
            )

    # --- Combat Handlers ---

    async def _handle_attack(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        # Step 1: Permission (always allowed in combat)
        # Step 2: Precondition
        hp = int(state.get("current_hp", 0))
        if hp <= 0:
            return ActionResult(success=False, action_type="attack", error="HP 为 0，无法行动")

        target = args.get("target", "未知目标")
        skill_id = args.get("skill_id")

        # Load skill data if specified
        multiplier = 1.0
        skill_name = "普通攻击"
        hit_count = 1
        cooldown = 1.5

        if skill_id:
            pool = get_pg()
            skill = await pool.fetchrow(
                "SELECT * FROM sword_skill_definitions WHERE id = $1", skill_id,
            )
            if not skill:
                return ActionResult(
                    success=False, action_type="attack",
                    error=f"未知剑技: {skill_id}",
                )

            level = int(state.get("level", 1))
            if level < skill["required_level"]:
                return ActionResult(
                    success=False, action_type="attack",
                    error=f"等级不足，{skill['name']}需要 Lv.{skill['required_level']}",
                )

            multiplier = skill["damage_multiplier"]
            skill_name = skill["name"]
            hit_count = skill["hit_count"]
            cooldown = skill["cooldown_seconds"]

        # Step 3: Get or create combat session with real monster data
        session = await get_combat(player_id)
        if not session:
            pool = get_pg()
            monster_def = await pool.fetchrow(
                "SELECT * FROM monster_definitions WHERE name = $1 OR name_en = $1 LIMIT 1",
                target,
            )
            if monster_def:
                session = await start_combat(player_id, dict(monster_def))
            else:
                session = await start_combat(player_id, {
                    "id": f"generic_{target}",
                    "name": target,
                    "monster_type": "unknown",
                    "hp": 100, "atk": 15, "defense": 5, "ac": 10,
                    "abilities_json": [],
                })

        monster = session.monster

        # Step 4: Computation
        dex_mod = _stat_mod(state.get("stat_dex", "10"))
        luk = int(state.get("stat_luk", "10"))

        # Get equipped weapon ATK
        weapon_atk = 10  # bare hands
        char_id = state.get("character_id")
        if char_id:
            try:
                pool = get_pg()
                equipped = await pool.fetchrow(
                    """SELECT id2.weapon_atk FROM character_inventory ci
                       JOIN item_definitions id2 ON ci.item_def_id = id2.id
                       WHERE ci.character_id = $1 AND ci.is_equipped = true
                       AND id2.item_type = 'weapon' LIMIT 1""",
                    uuid.UUID(char_id),
                )
                if equipped and equipped["weapon_atk"]:
                    weapon_atk = equipped["weapon_atk"]
            except Exception:
                pass

        # Attack roll (d20 + DEX mod) vs monster AC
        attack_roll = _roll(20, 1, dex_mod)
        hit = attack_roll["total"] >= monster.ac

        total_damage = 0
        hit_details = []

        if hit or attack_roll["natural_max"]:
            base_damage = weapon_atk * multiplier * (1 + int(state.get("stat_str", "10")) / 100)

            for i in range(hit_count):
                defense_reduction = monster.defense * 0.6
                raw = max(1, base_damage - defense_reduction)
                variance = random.uniform(0.9, 1.1)
                dmg = max(1, int(raw * variance))

                crit = False
                crit_mult = 1.0
                if random.random() < (0.01 + luk / 200):
                    crit = True
                    crit_mult = 1.5

                final_dmg = int(dmg * crit_mult)
                total_damage += final_dmg
                hit_details.append({"hit": i + 1, "damage": final_dmg, "critical": crit})

            monster.hp = max(0, monster.hp - total_damage)

        # Build description
        description = (
            f"使用 {skill_name} 攻击 {monster.name}。"
            f"攻击骰: d20({attack_roll['rolls'][0]})+{dex_mod}={attack_roll['total']} vs AC {monster.ac}。"
        )
        if hit or attack_roll["natural_max"]:
            description += f"命中！{hit_count}连击造成 {total_damage} 点伤害。"
            if any(h["critical"] for h in hit_details):
                description += "会心一击！"
            description += f"（{monster.name} HP: {monster.hp}/{monster.max_hp}）"
        else:
            description += "未命中。"

        state_changes = {}

        # Step 5: Post-attack resolution
        if monster.is_dead:
            description += f"\n{monster.name} 被击败了！"
            pool = get_pg()
            mdef = await pool.fetchrow(
                "SELECT exp_reward, col_reward_min, col_reward_max FROM monster_definitions WHERE id = $1",
                monster.monster_id,
            )
            exp_gain = mdef["exp_reward"] if mdef else 10
            col_gain = random.randint(
                mdef["col_reward_min"] or 0, max(mdef["col_reward_max"] or 0, 1)
            ) if mdef else 5
            description += f" 获得 {exp_gain} 经验值和 {col_gain} 珂尔。"

            state_changes["experience"] = int(state.get("experience", 0)) + exp_gain
            state_changes["col"] = int(state.get("col", 0)) + col_gain
            # Check level up
            level_up_msg = await _check_level_up(player_id, state, state_changes)
            if level_up_msg:
                description += level_up_msg
            else:
                await state_service.save_player_state(player_id, state_changes)
            await end_combat(player_id)

            # Quest progress: kill-type objectives
            try:
                progress_msgs = await quest_service.update_quest_progress(
                    player_id, "kill", monster.monster_id, 1,
                )
                for msg in progress_msgs:
                    description += f"\n{msg}"
            except Exception as e:
                logger.warning("Quest progress update failed: %s", e)
        else:
            # Monster counter-attack
            player_ac = 10 + _stat_mod(state.get("stat_agi", "10"))
            player_def = 0
            if char_id:
                try:
                    armor = await pool.fetchrow(
                        """SELECT id2.armor_defense FROM character_inventory ci
                           JOIN item_definitions id2 ON ci.item_def_id = id2.id
                           WHERE ci.character_id = $1 AND ci.is_equipped = true
                           AND id2.item_type = 'armor_body' LIMIT 1""",
                        uuid.UUID(char_id),
                    )
                    if armor and armor["armor_defense"]:
                        player_def = armor["armor_defense"]
                        player_ac += player_def // 5
                except Exception:
                    pass

            counter = calculate_counter_attack(monster, player_ac, player_def)
            description += f"\n{counter.description}"

            if counter.hits:
                new_hp = max(0, hp - counter.damage)
                state_changes["current_hp"] = new_hp
                await state_service.save_player_state(player_id, state_changes)
                if new_hp <= 0:
                    description += "\n你的HP归零了……角色死亡。"

            session.round_number += 1
            await update_combat(session)

        return ActionResult(
            success=True,
            action_type="attack",
            description=description,
            state_changes=state_changes,
            details={
                "attack_roll": attack_roll,
                "hit": hit or attack_roll["natural_max"],
                "skill_name": skill_name,
                "total_damage": total_damage,
                "hit_details": hit_details,
                "target": monster.name,
                "monster_hp": monster.hp,
                "monster_max_hp": monster.max_hp,
                "monster_dead": monster.is_dead,
            },
        )

    async def _handle_defend(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        return ActionResult(
            success=True,
            action_type="defend",
            description="进入防御姿态，AC+2 持续到下一回合。下次受到攻击时伤害减半。",
            details={"ac_bonus": 2, "duration": "1 round"},
        )

    async def _handle_use_item(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        item_id = args.get("item_id", "")
        pool = get_pg()

        # Check inventory
        char_id = state.get("character_id")
        if not char_id:
            return ActionResult(success=False, action_type="use_item", error="未创建角色")

        inv = await pool.fetchrow(
            """SELECT ci.*, id2.name, id2.item_type, id2.effect_json
               FROM character_inventory ci
               JOIN item_definitions id2 ON ci.item_def_id = id2.id
               WHERE ci.character_id = $1 AND ci.item_def_id = $2 AND ci.quantity > 0""",
            uuid.UUID(char_id), item_id,
        )
        if not inv:
            return ActionResult(
                success=False, action_type="use_item",
                error=f"背包中没有 {item_id}",
            )

        # Process item effect
        item_name = inv["name"]
        changes = {}

        if "heal" in item_id or "回复" in item_name:
            current_hp = int(state.get("current_hp", 0))
            max_hp = int(state.get("max_hp", 250))
            heal = min(100, max_hp - current_hp)  # Low potion heals 100
            new_hp = min(max_hp, current_hp + heal)
            changes["current_hp"] = new_hp
            description = f"使用{item_name}，回复 {heal} HP。当前 HP: {new_hp}/{max_hp}"
        elif "antidote" in item_id or "解毒" in item_name:
            description = f"使用{item_name}，解除中毒/麻痹状态。"
        elif "teleport" in item_id or "转移" in item_name:
            description = f"使用{item_name}。传送准备就绪，请指定目标楼层。"
        else:
            description = f"使用了{item_name}。"

        # Consume item
        await pool.execute(
            """UPDATE character_inventory SET quantity = quantity - 1
               WHERE character_id = $1 AND item_def_id = $2""",
            uuid.UUID(char_id), item_id,
        )

        # Apply state changes
        if changes:
            await state_service.save_player_state(player_id, changes)

        return ActionResult(
            success=True,
            action_type="use_item",
            description=description,
            state_changes=changes,
            details={"item_name": item_name, "item_id": item_id},
        )

    async def _handle_flee(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        agi_mod = _stat_mod(state.get("stat_agi", "10"))
        roll = _roll(20, 1, agi_mod)
        success = roll["total"] >= 12

        if success:
            return ActionResult(
                success=True, action_type="flee",
                description=f"逃跑检定: d20({roll['rolls'][0]})+{agi_mod}={roll['total']} >= 12，成功脱离战斗！",
                details={"roll": roll, "escaped": True},
            )
        return ActionResult(
            success=True, action_type="flee",
            description=f"逃跑检定: d20({roll['rolls'][0]})+{agi_mod}={roll['total']} < 12，逃跑失败！本回合无法行动。",
            details={"roll": roll, "escaped": False},
        )

    # --- Movement Handlers ---

    async def _handle_move_to(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        area = args.get("area", "")
        location = args.get("location", "")

        changes = {"current_area": area}
        if location:
            changes["current_location"] = location
        else:
            changes["current_location"] = area

        await state_service.save_player_state(player_id, changes)

        # Random encounter check (25% chance in wild areas)
        encounter = None
        safe_areas = ["起始之城", "城镇", "旅馆", "商店", "广场", "转移门", "酒馆"]
        if not any(s in area for s in safe_areas):
            if random.random() < 0.25:
                # Query actual monsters for current floor and area
                current_floor = int(state.get("current_floor", 1))
                try:
                    pool = get_pg()
                    monsters = await pool.fetch(
                        """SELECT name, level_min, level_max, monster_type
                           FROM monster_definitions
                           WHERE floor = $1 AND monster_type != 'boss'
                           ORDER BY random() LIMIT 1""",
                        current_floor,
                    )
                    if monsters:
                        m = monsters[0]
                        count = random.randint(1, 3) if m["monster_type"] != "mini_boss" else 1
                        if count == 1:
                            encounter = f"野外遭遇！一只 {m['name']}(Lv.{m['level_min']}) 出现了！"
                        else:
                            encounter = f"野外遭遇！{count}只 {m['name']}(Lv.{m['level_min']}-{m['level_max']}) 出现了！"
                    else:
                        encounter = "野外遭遇！附近出现了怪物的气息。"
                except Exception:
                    encounter = "野外遭遇！附近出现了怪物的气息。"

        description = f"移动到 {area}"
        if location:
            description += f" - {location}"
        if encounter:
            description += f"\n{encounter}"

        # Quest triggers: location-based + reach-type progress
        try:
            triggered = await quest_service.check_quest_triggers(
                player_id, state, "location", area,
            )
            if triggered:
                description += f"\n新任务可接取: {', '.join(triggered)}"

            progress_msgs = await quest_service.update_quest_progress(
                player_id, "reach", area, 1,
            )
            for msg in progress_msgs:
                description += f"\n{msg}"
        except Exception as e:
            logger.warning("Quest trigger check failed: %s", e)

        return ActionResult(
            success=True, action_type="move_to",
            description=description,
            state_changes=changes,
            details={"area": area, "location": location, "encounter": encounter},
        )

    async def _handle_enter_dungeon(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        dungeon = args.get("dungeon_name", "")
        changes = {"current_area": dungeon, "current_location": "入口"}
        await state_service.save_player_state(player_id, changes)

        return ActionResult(
            success=True, action_type="enter_dungeon",
            description=f"进入 {dungeon}。迷宫内光线昏暗，空气中弥漫着潮湿的气息。请小心行动。",
            state_changes=changes,
        )

    async def _handle_use_teleport_crystal(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        floor = args.get("floor", 1)
        if floor < 1 or floor > 7:
            return ActionResult(
                success=False, action_type="use_teleport_crystal",
                error=f"无法传送到第{floor}层，当前只开放1-7层",
            )

        floor_areas = {
            1: "起始之城", 2: "乌尔巴斯", 3: "兹姆福特",
            4: "罗毕亚", 5: "卡尔路因", 6: "史塔基翁", 7: "窝鲁布达",
        }
        area = floor_areas.get(floor, f"第{floor}层主街区")
        changes = {
            "current_floor": floor,
            "current_area": area,
            "current_location": "转移门广场",
        }
        await state_service.save_player_state(player_id, changes)

        return ActionResult(
            success=True, action_type="use_teleport_crystal",
            description=f"转移水晶闪耀蓝光——传送至第{floor}层 {area} 转移门广场。",
            state_changes=changes,
        )

    # --- Interaction Handlers ---

    async def _handle_talk_to_npc(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        npc_id = args.get("npc_id", "")
        topic = args.get("topic", "闲聊")

        # Load NPC data from PG for DM context
        pool = get_pg()
        npc_def = await pool.fetchrow(
            "SELECT * FROM npc_definitions WHERE id = $1 OR name = $1 OR name_en = $1 LIMIT 1",
            npc_id,
        )

        npc_name = npc_id
        npc_context = ""
        actual_npc_id = npc_id

        if npc_def:
            actual_npc_id = npc_def["id"]
            npc_name = npc_def["name"]
            npc_context = (
                f"[NPC信息] {npc_def['name']}({npc_def['name_en']}) - {npc_def['npc_type']}\n"
                f"外貌: {npc_def['appearance'] or '无描述'}\n"
                f"性格: {npc_def['personality'] or '无描述'}\n"
                f"说话风格: {npc_def['dialog_style'] or '无特别说明'}"
            )

        # Get relationship with this NPC
        rel = await npc_relationship_service.get_relationship(player_id, actual_npc_id)
        rel_tier = npc_relationship_service.get_relationship_tier(rel["level"])

        # Update interaction count (+1 relationship per conversation)
        new_level = await npc_relationship_service.update_relationship(
            player_id, actual_npc_id, 1,
            interaction_summary=f"对话话题: {topic}",
        )

        # Check quest triggers (npc_talk type)
        triggered = await quest_service.check_quest_triggers(
            player_id, state, "npc_talk", actual_npc_id,
        )

        # Also update progress for talk-type objectives
        progress_msgs = await quest_service.update_quest_progress(
            player_id, "talk", actual_npc_id, 1,
        )

        description = f"与 {npc_name} 对话，话题：{topic}。"
        description += f"（关系: {rel_tier} [{rel['level']}→{new_level}]）"
        if npc_context:
            description += f"\n{npc_context}"
        if triggered:
            description += f"\n新任务可接取: {', '.join(triggered)}"
        for msg in progress_msgs:
            description += f"\n{msg}"

        return ActionResult(
            success=True, action_type="talk_to_npc",
            description=description,
            details={
                "npc_id": actual_npc_id,
                "npc_name": npc_name,
                "topic": topic,
                "relationship": new_level,
                "relationship_tier": rel_tier,
                "quests_triggered": triggered,
            },
        )

    async def _handle_trade(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        npc_id = args.get("npc_id", "")
        action = args.get("action", "buy")
        item_id = args.get("item_id", "")
        quantity = args.get("quantity", 1)

        pool = get_pg()
        item_def = await pool.fetchrow(
            "SELECT * FROM item_definitions WHERE id = $1", item_id,
        )
        if not item_def:
            return ActionResult(
                success=False, action_type="trade", error=f"未知物品: {item_id}",
            )

        col = int(state.get("col", 0))
        total_price = item_def["base_price"] * quantity

        if action == "buy":
            if col < total_price:
                return ActionResult(
                    success=False, action_type="trade",
                    error=f"珂尔不足。需要 {total_price} Col，当前 {col} Col",
                )
            changes = {"col": col - total_price}
            await state_service.save_player_state(player_id, changes)

            char_id = state.get("character_id")
            if char_id:
                await pool.execute(
                    """INSERT INTO character_inventory (character_id, item_def_id, quantity, current_durability)
                       VALUES ($1, $2, $3, $4)""",
                    uuid.UUID(char_id), item_id, quantity, item_def["weapon_durability"],
                )

            return ActionResult(
                success=True, action_type="trade",
                description=f"从 {npc_id} 购买了 {item_def['name']} ×{quantity}，花费 {total_price} Col。",
                state_changes=changes,
            )
        else:  # sell
            sell_price = total_price // 2
            changes = {"col": col + sell_price}
            await state_service.save_player_state(player_id, changes)

            return ActionResult(
                success=True, action_type="trade",
                description=f"向 {npc_id} 出售了 {item_def['name']} ×{quantity}，获得 {sell_price} Col。",
                state_changes=changes,
            )

    async def _handle_accept_quest(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        quest_id = args.get("quest_id", "")
        if not quest_id:
            return ActionResult(
                success=False, action_type="accept_quest",
                error="需要指定 quest_id",
            )

        result = await quest_service.accept_quest(player_id, quest_id)
        if not result["success"]:
            return ActionResult(
                success=False, action_type="accept_quest",
                error=result["message"],
            )

        # Fetch quest description for DM context
        pool = get_pg()
        qdef = await pool.fetchrow(
            "SELECT description, objectives_json FROM quest_definitions WHERE id = $1",
            quest_id,
        )
        objectives_text = ""
        if qdef:
            objectives = qdef["objectives_json"] or []
            if isinstance(objectives, str):
                objectives = json.loads(objectives)
            obj_lines = [f"  - {o.get('desc', o.get('target', ''))}" for o in objectives]
            if obj_lines:
                objectives_text = "\n目标:\n" + "\n".join(obj_lines)

        return ActionResult(
            success=True, action_type="accept_quest",
            description=f"{result['message']}。{objectives_text}",
            details={"quest_id": quest_id, "quest_name": result["quest_name"]},
        )

    async def _handle_inspect(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        target = args.get("target", "")
        int_mod = _stat_mod(state.get("stat_int", "10"))
        roll = _roll(20, 1, int_mod)
        dc = roll["total"]

        pool = get_pg()
        info = ""

        # Try to match against monster definitions
        monster = await pool.fetchrow(
            "SELECT name, monster_type, level_min, level_max, hp, atk, defense, ac, weaknesses, description "
            "FROM monster_definitions WHERE name = $1 OR name_en = $1 LIMIT 1",
            target,
        )
        if monster:
            info = f"[怪物] {monster['name']} ({monster['monster_type']}) Lv.{monster['level_min']}-{monster['level_max']}"
            if dc >= 10:
                info += f"\nHP: {monster['hp']} | ATK: {monster['atk']} | DEF: {monster['defense']} | AC: {monster['ac']}"
            if dc >= 15 and monster["weaknesses"]:
                info += f"\n弱点: {monster['weaknesses']}"
            if dc >= 18 and monster["description"]:
                info += f"\n{monster['description'][:150]}"
        else:
            # Try NPC
            npc = await pool.fetchrow(
                "SELECT name, npc_type, appearance, personality, description "
                "FROM npc_definitions WHERE name = $1 OR name_en = $1 OR id = $1 LIMIT 1",
                target,
            )
            if npc:
                info = f"[NPC] {npc['name']} ({npc['npc_type']})"
                if dc >= 8 and npc["appearance"]:
                    info += f"\n{npc['appearance'][:120]}"
                if dc >= 14 and npc["personality"]:
                    info += f"\n性格: {npc['personality'][:100]}"
            else:
                # Try item
                item = await pool.fetchrow(
                    "SELECT name, item_type, rarity, description, weapon_atk, armor_defense "
                    "FROM item_definitions WHERE name = $1 OR id = $1 LIMIT 1",
                    target,
                )
                if item:
                    info = f"[物品] {item['name']} ({item['rarity']} {item['item_type']})"
                    if item["weapon_atk"]:
                        info += f" ATK {item['weapon_atk']}"
                    if item["armor_defense"]:
                        info += f" DEF {item['armor_defense']}"
                    if dc >= 10 and item["description"]:
                        info += f"\n{item['description'][:150]}"

        description = f"检查 {target}。鉴定检定: d20({roll['rolls'][0]})+{int_mod}={dc}。"
        if info:
            description += f"\n{info}"
        else:
            description += "（DM 将根据检定结果描述发现）"

        return ActionResult(
            success=True, action_type="inspect",
            description=description,
            details={"target": target, "roll": roll, "info_found": bool(info)},
        )

    # --- Character Handlers ---

    async def _handle_check_status(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        if not state:
            return ActionResult(
                success=False, action_type="check_status", error="未创建角色",
            )

        return ActionResult(
            success=True, action_type="check_status",
            description=(
                f"【角色状态】\n"
                f"名称: {state.get('name', '???')} | Lv.{state.get('level', 1)}\n"
                f"HP: {state.get('current_hp', '?')}/{state.get('max_hp', '?')}\n"
                f"STR {state.get('stat_str', 10)} | AGI {state.get('stat_agi', 10)} | "
                f"VIT {state.get('stat_vit', 10)} | INT {state.get('stat_int', 10)} | "
                f"DEX {state.get('stat_dex', 10)} | LUK {state.get('stat_luk', 10)}\n"
                f"Col: {state.get('col', 0)}\n"
                f"位置: 第{state.get('current_floor', 1)}层 "
                f"{state.get('current_area', '起始之城')} {state.get('current_location', '')}"
            ),
        )

    async def _handle_check_inventory(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        char_id = state.get("character_id")
        if not char_id:
            return ActionResult(
                success=False, action_type="check_inventory", error="未创建角色",
            )

        pool = get_pg()
        items = await pool.fetch(
            """SELECT ci.quantity, ci.enhancement_level, ci.enhancement_detail,
                      ci.is_equipped, ci.equipped_slot, id2.name, id2.item_type, id2.rarity
               FROM character_inventory ci
               JOIN item_definitions id2 ON ci.item_def_id = id2.id
               WHERE ci.character_id = $1 AND ci.quantity > 0
               ORDER BY ci.is_equipped DESC, id2.item_type""",
            uuid.UUID(char_id),
        )

        if not items:
            return ActionResult(
                success=True, action_type="check_inventory",
                description="【背包】空空如也。",
            )

        lines = ["【背包】"]
        for item in items:
            name = item["name"]
            if item["enhancement_level"] > 0:
                name += f"+{item['enhancement_level']}"
                if item["enhancement_detail"]:
                    name += f"({item['enhancement_detail']})"
            equipped = " [装备中]" if item["is_equipped"] else ""
            qty = f" ×{item['quantity']}" if item["quantity"] > 1 else ""
            lines.append(f"  {name}{qty}{equipped}")

        return ActionResult(
            success=True, action_type="check_inventory",
            description="\n".join(lines),
        )

    async def _handle_equip_item(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        item_id = args.get("item_id", "")
        slot = args.get("slot", "")

        char_id = state.get("character_id")
        if not char_id:
            return ActionResult(success=False, action_type="equip_item", error="未创建角色")

        pool = get_pg()

        # Find the item in inventory
        inv = await pool.fetchrow(
            """SELECT ci.id AS inv_id, ci.is_equipped, ci.equipped_slot,
                      id2.name, id2.item_type, id2.weapon_atk, id2.armor_defense
               FROM character_inventory ci
               JOIN item_definitions id2 ON ci.item_def_id = id2.id
               WHERE ci.character_id = $1 AND ci.item_def_id = $2 AND ci.quantity > 0""",
            uuid.UUID(char_id), item_id,
        )
        if not inv:
            return ActionResult(
                success=False, action_type="equip_item",
                error=f"背包中没有 {item_id}",
            )

        if inv["is_equipped"]:
            return ActionResult(
                success=False, action_type="equip_item",
                error=f"{inv['name']} 已在装备中",
            )

        # Determine slot from item_type if not specified
        item_type = inv["item_type"]
        if not slot:
            slot_map = {
                "weapon": "main_hand",
                "armor_body": "body",
                "armor_head": "head",
                "armor_legs": "legs",
                "shield": "off_hand",
            }
            slot = slot_map.get(item_type, "main_hand")

        # Unequip current item in same slot
        await pool.execute(
            """UPDATE character_inventory
               SET is_equipped = false, equipped_slot = NULL
               WHERE character_id = $1 AND equipped_slot = $2 AND is_equipped = true""",
            uuid.UUID(char_id), slot,
        )

        # Equip the new item
        await pool.execute(
            """UPDATE character_inventory
               SET is_equipped = true, equipped_slot = $1
               WHERE id = $2""",
            slot, inv["inv_id"],
        )

        stat_info = ""
        if inv["weapon_atk"]:
            stat_info = f" (ATK {inv['weapon_atk']})"
        elif inv["armor_defense"]:
            stat_info = f" (DEF {inv['armor_defense']})"

        return ActionResult(
            success=True, action_type="equip_item",
            description=f"装备了 {inv['name']}{stat_info} 到 {slot} 槽位。",
            details={"item_id": item_id, "item_name": inv["name"], "slot": slot},
        )

    async def _handle_rest(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        rest_type = args.get("rest_type", "short")
        current_hp = int(state.get("current_hp", 0))
        max_hp = int(state.get("max_hp", 250))

        if rest_type == "long":
            new_hp = max_hp
            description = f"在旅馆进行长休（8小时），HP 完全恢复: {max_hp}/{max_hp}"
        else:
            heal = max_hp // 4
            new_hp = min(max_hp, current_hp + heal)
            description = f"短休（1小时），恢复 {heal} HP。当前 HP: {new_hp}/{max_hp}"

        changes = {"current_hp": new_hp}
        await state_service.save_player_state(player_id, changes)

        return ActionResult(
            success=True, action_type="rest",
            description=description,
            state_changes=changes,
        )

    async def _handle_roll_dice(
        self, player_id: str, state: dict, args: dict
    ) -> ActionResult:
        sides = args.get("sides", 20)
        count = args.get("count", 1)
        modifier = args.get("modifier", 0)

        result = _roll(sides, count, modifier)
        dice_str = f"{count}d{sides}" + (f"+{modifier}" if modifier > 0 else f"{modifier}" if modifier < 0 else "")

        return ActionResult(
            success=True, action_type="roll_dice",
            description=f"骰子检定 {dice_str}: {result['rolls']} + {modifier} = {result['total']}",
            details=result,
        )
