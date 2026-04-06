"""ReAct tool definitions for OpenAI function calling format."""

from __future__ import annotations

GAME_TOOLS: list[dict] = [
    # --- Combat ---
    {
        "type": "function",
        "function": {
            "name": "attack",
            "description": "使用剑技或普通攻击攻击目标。系统将自动计算命中（d20+DEX）、伤害（ATK×倍率）和会心判定。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "剑技ID（如 sword_slant, rapier_linear）。留空则为普通攻击。",
                    },
                    "target": {
                        "type": "string",
                        "description": "攻击目标名称（如 哥布林, 狗头人守卫）",
                    },
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "defend",
            "description": "进入防御姿态，AC+2持续到下一回合。适合在等待队友切换或恢复时使用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_item",
            "description": "使用背包中的消耗品。如回复药水恢复HP，解毒药水解除异常状态，转移水晶传送。",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "物品ID（如 potion_heal_low, crystal_teleport）",
                    },
                    "target": {
                        "type": "string",
                        "description": "目标（默认自己，可指定队友名）",
                    },
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flee",
            "description": "尝试从战斗中逃跑。需要通过AGI检定（d20+AGI_mod >= 12）。失败则无法行动一回合。",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "逃跑方向（如 北, 入口方向, 来时的路）",
                    },
                },
                "required": ["direction"],
            },
        },
    },
    # --- Movement ---
    {
        "type": "function",
        "function": {
            "name": "move_to",
            "description": "移动到指定区域或地点。在安全区内自由移动，野外可能遭遇怪物。",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "目标区域（如 起始之城, 迷雾森林, 霍仑卡村）",
                    },
                    "location": {
                        "type": "string",
                        "description": "具体地点（如 武器店, 旅馆, 广场）",
                    },
                },
                "required": ["area"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enter_dungeon",
            "description": "进入迷宫或地下城。将面临更强的怪物和更好的掉落。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dungeon_name": {
                        "type": "string",
                        "description": "迷宫名称（如 第1层迷宫塔, 暗黑精灵地下通道）",
                    },
                },
                "required": ["dungeon_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_teleport_crystal",
            "description": "使用转移水晶传送到已开通的楼层转移门。消耗一个转移水晶。",
            "parameters": {
                "type": "object",
                "properties": {
                    "floor": {
                        "type": "integer",
                        "description": "目标楼层数（1-7）",
                    },
                },
                "required": ["floor"],
            },
        },
    },
    # --- Interaction ---
    {
        "type": "function",
        "function": {
            "name": "talk_to_npc",
            "description": "与NPC对话。可以获取信息、触发任务、交易、或改变好感度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_id": {
                        "type": "string",
                        "description": "NPC名称或ID（如 基滋梅尔, 亚鲁戈, 武器店老板）",
                    },
                    "topic": {
                        "type": "string",
                        "description": "对话主题（如 任务, 交易, 情报, 闲聊）",
                    },
                },
                "required": ["npc_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trade",
            "description": "与NPC进行买卖交易。",
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_id": {
                        "type": "string",
                        "description": "NPC名称",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "买入或卖出",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "物品ID",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "数量（默认1）",
                    },
                },
                "required": ["npc_id", "action", "item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "accept_quest",
            "description": "接受一个可用的任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "quest_id": {
                        "type": "string",
                        "description": "任务ID",
                    },
                },
                "required": ["quest_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect",
            "description": "检查或鉴定目标。可以查看怪物弱点、物品属性、环境线索等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "检查目标（物品名/怪物名/环境描述）",
                    },
                },
                "required": ["target"],
            },
        },
    },
    # --- Character ---
    {
        "type": "function",
        "function": {
            "name": "check_status",
            "description": "查看角色当前完整状态：HP、属性、位置、装备、技能等。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "查看背包中的所有物品。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "equip_item",
            "description": "装备一个物品到指定槽位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "背包中的物品ID",
                    },
                    "slot": {
                        "type": "string",
                        "enum": ["main_hand", "off_hand", "body", "accessory"],
                        "description": "装备槽位",
                    },
                },
                "required": ["item_id", "slot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rest",
            "description": "休息恢复。短休恢复25%HP（1小时），长休恢复100%HP（8小时，需在旅馆或安全区）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "rest_type": {
                        "type": "string",
                        "enum": ["short", "long"],
                        "description": "短休或长休",
                    },
                },
                "required": ["rest_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "投掷骰子进行检定。用于技能检定、运气判定等非战斗场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "骰子面数（默认20）",
                    },
                    "count": {
                        "type": "integer",
                        "description": "骰子数量（默认1）",
                    },
                    "modifier": {
                        "type": "integer",
                        "description": "修正值",
                    },
                },
            },
        },
    },
]
