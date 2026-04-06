"""Combat state management using Redis.

Manages ephemeral combat sessions with monster HP tracking,
round counting, and auto-counterattack logic.

Redis key: sao:combat:{player_id} → HASH, TTL 30min
Fields:
  - monster_id: str
  - monster_name: str
  - monster_hp: int (current)
  - monster_max_hp: int
  - monster_atk: int
  - monster_defense: int
  - monster_ac: int
  - monster_abilities: JSON string
  - round_number: int
  - is_boss: "0" or "1"
  - hp_bars_remaining: int (for bosses with multi-HP-bar)
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field

from gameserver.db.redis_client import get_redis

logger = logging.getLogger(__name__)

COMBAT_TTL = 1800  # 30 minutes


@dataclass
class MonsterState:
    """Runtime state of a monster in combat."""
    monster_id: str
    name: str
    hp: int
    max_hp: int
    atk: int
    defense: int
    ac: int
    abilities: list[dict] = field(default_factory=list)
    is_boss: bool = False
    hp_bars_remaining: int = 1

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def hp_percent(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0


@dataclass
class CombatSession:
    """Full combat session state."""
    player_id: str
    monster: MonsterState
    round_number: int = 1

    def to_redis_hash(self) -> dict[str, str]:
        return {
            "monster_id": self.monster.monster_id,
            "monster_name": self.monster.name,
            "monster_hp": str(self.monster.hp),
            "monster_max_hp": str(self.monster.max_hp),
            "monster_atk": str(self.monster.atk),
            "monster_defense": str(self.monster.defense),
            "monster_ac": str(self.monster.ac),
            "monster_abilities": json.dumps(self.monster.abilities, ensure_ascii=False),
            "is_boss": "1" if self.monster.is_boss else "0",
            "hp_bars_remaining": str(self.monster.hp_bars_remaining),
            "round_number": str(self.round_number),
        }

    @classmethod
    def from_redis_hash(cls, player_id: str, data: dict[str, str]) -> CombatSession:
        abilities = []
        try:
            abilities = json.loads(data.get("monster_abilities", "[]"))
        except (json.JSONDecodeError, TypeError):
            pass

        monster = MonsterState(
            monster_id=data["monster_id"],
            name=data["monster_name"],
            hp=int(data["monster_hp"]),
            max_hp=int(data["monster_max_hp"]),
            atk=int(data["monster_atk"]),
            defense=int(data["monster_defense"]),
            ac=int(data.get("monster_ac", "10")),
            abilities=abilities,
            is_boss=data.get("is_boss") == "1",
            hp_bars_remaining=int(data.get("hp_bars_remaining", "1")),
        )
        return cls(
            player_id=player_id,
            monster=monster,
            round_number=int(data.get("round_number", "1")),
        )


def _combat_key(player_id: str) -> str:
    return f"sao:combat:{player_id}"


async def start_combat(
    player_id: str,
    monster_def: dict,
) -> CombatSession:
    """Start a new combat session from a monster_definitions row.

    Args:
        player_id: The player's UUID
        monster_def: Dict with monster definition fields (from PG or YAML)

    Returns:
        New CombatSession stored in Redis
    """
    abilities = monster_def.get("abilities_json", [])
    if isinstance(abilities, str):
        try:
            abilities = json.loads(abilities)
        except (json.JSONDecodeError, TypeError):
            abilities = []

    is_boss = monster_def.get("monster_type") == "boss"
    hp = int(monster_def["hp"])

    monster = MonsterState(
        monster_id=monster_def["id"],
        name=monster_def["name"],
        hp=hp,
        max_hp=hp,
        atk=int(monster_def["atk"]),
        defense=int(monster_def["defense"]),
        ac=int(monster_def.get("ac", 10)),
        abilities=abilities,
        is_boss=is_boss,
        hp_bars_remaining=4 if is_boss else 1,
    )

    session = CombatSession(player_id=player_id, monster=monster)
    r = get_redis()
    key = _combat_key(player_id)
    await r.delete(key)
    await r.hset(key, mapping=session.to_redis_hash())
    await r.expire(key, COMBAT_TTL)

    logger.info("Combat started: %s vs %s (HP: %d)", player_id[:8], monster.name, monster.hp)
    return session


async def get_combat(player_id: str) -> CombatSession | None:
    """Get the active combat session for a player, or None."""
    r = get_redis()
    data = await r.hgetall(_combat_key(player_id))
    if not data:
        return None
    return CombatSession.from_redis_hash(player_id, data)


async def update_combat(session: CombatSession) -> None:
    """Persist updated combat state to Redis."""
    r = get_redis()
    key = _combat_key(session.player_id)
    await r.hset(key, mapping=session.to_redis_hash())
    await r.expire(key, COMBAT_TTL)


async def end_combat(player_id: str) -> None:
    """End and clean up a combat session."""
    r = get_redis()
    await r.delete(_combat_key(player_id))
    logger.info("Combat ended for %s", player_id[:8])


@dataclass
class CounterAttackResult:
    """Result of a monster's counter-attack."""
    attack_roll: int
    hits: bool
    damage: int
    description: str


def calculate_counter_attack(
    monster: MonsterState,
    player_ac: int,
    player_defense: int = 0,
) -> CounterAttackResult:
    """Calculate monster's automatic counter-attack after player's turn.

    Uses d20 vs player AC, then damage formula:
        raw_damage = monster_atk - player_defense * 0.6
        final_damage = raw_damage * random(0.9, 1.1)

    Args:
        monster: Current monster state
        player_ac: Player's armor class
        player_defense: Player's defense value (from equipped armor)

    Returns:
        CounterAttackResult with roll, hit status, damage, and description
    """
    # d20 attack roll
    attack_roll = random.randint(1, 20)
    hits = attack_roll >= player_ac

    if not hits:
        return CounterAttackResult(
            attack_roll=attack_roll,
            hits=False,
            damage=0,
            description=f"{monster.name}发动反击（骰子: {attack_roll} vs AC {player_ac}），但被闪避了！",
        )

    # Damage calculation
    raw_damage = monster.atk - player_defense * 0.6
    raw_damage = max(1, raw_damage)
    variance = random.uniform(0.9, 1.1)
    final_damage = max(1, int(raw_damage * variance))

    # Natural 20 = critical
    if attack_roll == 20:
        final_damage = int(final_damage * 1.5)
        desc = (
            f"{monster.name}发动反击（骰子: 20 - 会心一击！），"
            f"造成 {final_damage} 点伤害！"
        )
    else:
        desc = (
            f"{monster.name}发动反击（骰子: {attack_roll} vs AC {player_ac}），"
            f"命中！造成 {final_damage} 点伤害。"
        )

    return CounterAttackResult(
        attack_roll=attack_roll,
        hits=True,
        damage=final_damage,
        description=desc,
    )
