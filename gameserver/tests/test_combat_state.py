"""Tests for combat_state module."""

import json
import pytest

from gameserver.game.combat_state import (
    MonsterState,
    CombatSession,
    start_combat,
    end_combat,
    get_combat,
)


class TestMonsterState:
    """Tests for MonsterState dataclass."""

    def test_monster_state_is_dead(self):
        """HP 为 0 时返回 True."""
        monster = MonsterState(
            monster_id="test_001",
            name="Test Monster",
            hp=0,
            max_hp=100,
            atk=10,
            defense=5,
            ac=12,
        )
        assert monster.is_dead is True

    def test_monster_state_is_alive(self):
        """HP > 0 时返回 False."""
        monster = MonsterState(
            monster_id="test_001",
            name="Test Monster",
            hp=50,
            max_hp=100,
            atk=10,
            defense=5,
            ac=12,
        )
        assert monster.is_dead is False

    def test_monster_state_hp_percent(self):
        """百分比计算正确."""
        monster = MonsterState(
            monster_id="test_001",
            name="Test Monster",
            hp=50,
            max_hp=100,
            atk=10,
            defense=5,
            ac=12,
        )
        assert monster.hp_percent == 0.5

    def test_monster_state_hp_percent_zero_max(self):
        """max_hp 为 0 时返回 0."""
        monster = MonsterState(
            monster_id="test_001",
            name="Test Monster",
            hp=0,
            max_hp=0,
            atk=10,
            defense=5,
            ac=12,
        )
        assert monster.hp_percent == 0


class TestCombatSession:
    """Tests for CombatSession dataclass."""

    def test_combat_session_redis_serialization(self):
        """to_redis_hash/from_redis_hash 往返一致."""
        monster = MonsterState(
            monster_id="test_001",
            name="Test Monster",
            hp=80,
            max_hp=100,
            atk=15,
            defense=5,
            ac=12,
            abilities=[{"name": "bite", "damage": 1.2}],
            is_boss=False,
            hp_bars_remaining=1,
        )
        session = CombatSession(
            player_id="player_001",
            monster=monster,
            round_number=3,
        )

        # Serialize to Redis hash
        redis_hash = session.to_redis_hash()

        # Deserialize from Redis hash
        restored = CombatSession.from_redis_hash("player_001", redis_hash)

        assert restored.player_id == session.player_id
        assert restored.monster.monster_id == session.monster.monster_id
        assert restored.monster.name == session.monster.name
        assert restored.monster.hp == session.monster.hp
        assert restored.monster.max_hp == session.monster.max_hp
        assert restored.monster.atk == session.monster.atk
        assert restored.monster.defense == session.monster.defense
        assert restored.monster.ac == session.monster.ac
        assert restored.monster.abilities == session.monster.abilities
        assert restored.monster.is_boss == session.monster.is_boss
        assert restored.monster.hp_bars_remaining == session.monster.hp_bars_remaining
        assert restored.round_number == session.round_number

    def test_combat_session_from_redis_hash_with_defaults(self):
        """从 Redis hash 恢复时使用默认值处理缺失字段."""
        data = {
            "monster_id": "test_001",
            "monster_name": "Test Monster",
            "monster_hp": "80",
            "monster_max_hp": "100",
            "monster_atk": "15",
            "monster_defense": "5",
            # monster_ac 缺失
            "monster_abilities": "[]",
            "is_boss": "0",
            # hp_bars_remaining 缺失
            # round_number 缺失
        }
        session = CombatSession.from_redis_hash("player_001", data)

        assert session.monster.ac == 10  # 默认值
        assert session.monster.hp_bars_remaining == 1  # 默认值
        assert session.round_number == 1  # 默认值


class TestCombatOperations:
    """Tests for combat operations with mocked Redis."""

    @pytest.mark.asyncio
    async def test_start_combat(self, fake_redis, player_id, sample_monster_def):
        """创建战斗会话并写入 Redis（mock Redis）."""
        session = await start_combat(player_id, sample_monster_def)

        assert session.player_id == player_id
        assert session.monster.monster_id == sample_monster_def["id"]
        assert session.monster.name == sample_monster_def["name"]
        assert session.monster.hp == sample_monster_def["hp"]
        assert session.monster.max_hp == sample_monster_def["hp"]
        assert session.monster.atk == sample_monster_def["atk"]
        assert session.monster.defense == sample_monster_def["defense"]
        assert session.monster.ac == sample_monster_def["ac"]
        assert session.monster.abilities == sample_monster_def["abilities_json"]
        assert session.monster.is_boss is False
        assert session.monster.hp_bars_remaining == 1
        assert session.round_number == 1

        # Verify Redis storage
        key = f"sao:combat:{player_id}"
        stored_data = await fake_redis.hgetall(key)
        assert stored_data is not None
        assert stored_data["monster_id"] == sample_monster_def["id"]
        assert stored_data["monster_name"] == sample_monster_def["name"]

    @pytest.mark.asyncio
    async def test_start_combat_boss(self, fake_redis, player_id):
        """创建 Boss 战斗会话."""
        boss_def = {
            "id": "boss_001",
            "name": "Test Boss",
            "monster_type": "boss",
            "hp": 500,
            "atk": 50,
            "defense": 20,
            "ac": 15,
            "abilities_json": [],
        }
        session = await start_combat(player_id, boss_def)

        assert session.monster.is_boss is True
        assert session.monster.hp_bars_remaining == 4

    @pytest.mark.asyncio
    async def test_end_combat(self, fake_redis, player_id, sample_monster_def):
        """删除 Redis key（mock Redis）."""
        # First start a combat
        await start_combat(player_id, sample_monster_def)

        # Verify it exists
        key = f"sao:combat:{player_id}"
        stored_data = await fake_redis.hgetall(key)
        assert stored_data is not None
        assert stored_data["monster_id"] == sample_monster_def["id"]

        # End combat
        await end_combat(player_id)

        # Verify it's deleted
        stored_data = await fake_redis.hgetall(key)
        assert stored_data == {} or stored_data is None

    @pytest.mark.asyncio
    async def test_get_combat_existing(self, fake_redis, player_id, sample_monster_def):
        """获取已存在的战斗会话."""
        # Start combat first
        await start_combat(player_id, sample_monster_def)

        # Get combat
        session = await get_combat(player_id)

        assert session is not None
        assert session.player_id == player_id
        assert session.monster.monster_id == sample_monster_def["id"]

    @pytest.mark.asyncio
    async def test_get_combat_nonexistent(self, fake_redis, player_id):
        """获取不存在的战斗会话返回 None."""
        session = await get_combat(player_id)
        assert session is None
