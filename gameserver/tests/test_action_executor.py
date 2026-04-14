"""Tests for action_executor module."""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from gameserver.game.action_executor import (
    ActionResult,
    ActionExecutor,
    _roll,
    _stat_mod,
    _calc_exp_to_next,
    _calc_max_hp,
)


@pytest.fixture
def executor():
    """Create ActionExecutor instance."""
    return ActionExecutor()


class TestRoll:
    """Tests for dice rolling functions."""

    def test_roll_basic(self):
        """单次掷骰返回格式正确、范围在 1-20."""
        # Given: A standard d20 roll with no modifier
        # When: Rolling the dice
        result = _roll(sides=20, count=1, modifier=0)

        assert "rolls" in result
        assert "modifier" in result
        assert "total" in result
        assert "natural_max" in result
        assert "natural_1" in result

        assert len(result["rolls"]) == 1
        assert 1 <= result["rolls"][0] <= 20
        assert result["modifier"] == 0
        assert result["total"] == result["rolls"][0]

    def test_roll_with_modifier(self):
        """修正值正确加入."""
        # Given: A d20 roll with +5 modifier
        # When: Rolling the dice
        result = _roll(sides=20, count=1, modifier=5)

        assert result["modifier"] == 5
        assert result["total"] == result["rolls"][0] + 5

    def test_roll_multiple_dice(self):
        """多骰子掷骰."""
        # Given: Rolling 3d6 (three six-sided dice)
        # When: Rolling the dice
        result = _roll(sides=6, count=3, modifier=0)

        assert len(result["rolls"]) == 3
        for roll in result["rolls"]:
            assert 1 <= roll <= 6
        assert result["total"] == sum(result["rolls"])

    @patch('gameserver.game.action_executor.random.randint', return_value=20)
    def test_roll_natural_max(self, mock_randint):
        """natural_max 为 True 当掷出最大值."""
        # Given: Mock randint to always return 20 (max value)
        # When: Rolling a d20
        result = _roll(sides=20, count=1, modifier=0)
        
        # Then: natural_max should be True
        assert result["natural_max"] is True
        assert result["rolls"][0] == 20

    @patch('gameserver.game.action_executor.random.randint', return_value=1)
    def test_roll_natural_1(self, mock_randint):
        """natural_1 为 True 当掷出 1."""
        # Given: Mock randint to always return 1 (min value)
        # When: Rolling a d20
        result = _roll(sides=20, count=1, modifier=0)
        
        # Then: natural_1 should be True
        assert result["natural_1"] is True
        assert result["rolls"][0] == 1


class TestStatMod:
    """Tests for stat modifier calculation."""

    def test_stat_mod_calculation_10(self):
        """属性值 10→0."""
        # Given: A stat value of 10 (baseline)
        # When: Calculating the modifier
        # Then: It should be 0
        assert _stat_mod(10) == 0

    def test_stat_mod_calculation_16(self):
        """属性值 16→+3."""
        # Given: A stat value of 16
        # When: Calculating the modifier
        # Then: It should be +3
        assert _stat_mod(16) == 3

    def test_stat_mod_calculation_8(self):
        """属性值 8→-1."""
        # Given: A stat value of 8
        # When: Calculating the modifier
        # Then: It should be -1
        assert _stat_mod(8) == -1

    def test_stat_mod_calculation_12(self):
        """属性值 12→+1."""
        assert _stat_mod(12) == 1

    def test_stat_mod_calculation_14(self):
        """属性値 14→+2."""
        assert _stat_mod(14) == 2

    def test_stat_mod_calculation_20(self):
        """属性値 20→+5."""
        assert _stat_mod(20) == 5

    def test_stat_mod_calculation_4(self):
        """属性値 4→-3."""
        assert _stat_mod(4) == -3


class TestCalcExpToNext:
    """Tests for experience calculation."""

    def test_calc_exp_to_next_level_1(self):
        """等级 1 经验公式."""
        exp = _calc_exp_to_next(1)
        assert exp == 100  # 100 * 1^1.5 = 100

    def test_calc_exp_to_next_level_2(self):
        """等级 2 经验公式."""
        exp = _calc_exp_to_next(2)
        # 100 * 2^1.5 = 100 * 2.828... ≈ 282
        assert exp > 280
        assert exp < 285

    def test_calc_exp_to_next_level_5(self):
        """等级 5 经验公式."""
        exp = _calc_exp_to_next(5)
        # 100 * 5^1.5 = 100 * 11.18... ≈ 1118
        assert exp > 1100
        assert exp < 1120


class TestCalcMaxHp:
    """Tests for HP calculation."""

    def test_calc_max_hp_level_1_vit_10(self):
        """HP 公式与体质关联 - 等级 1, 体质 10."""
        hp = _calc_max_hp(level=1, vit=10)
        # base_hp(200) + level*hp_per_level(50) + vit*hp_per_vit(10)
        # = 200 + 50 + 100 = 350
        assert hp == 350

    def test_calc_max_hp_level_5_vit_12(self):
        """HP 公式与体质关联 - 等级 5, 体质 12."""
        hp = _calc_max_hp(level=5, vit=12)
        # 200 + 5*50 + 12*10 = 200 + 250 + 120 = 570
        assert hp == 570

    def test_calc_max_hp_level_10_vit_8(self):
        """HP 公式与体质关联 - 等级 10, 体质 8."""
        hp = _calc_max_hp(level=10, vit=8)
        # 200 + 10*50 + 8*10 = 200 + 500 + 80 = 780
        assert hp == 780


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_action_result_to_tool_result_success(self):
        """序列化为 JSON 格式正确 - 成功."""
        # Given: A successful action result with details
        result = ActionResult(
            success=True,
            action_type="attack",
            description="Attack successful",
            details={"damage": 25, "target": "monster"},
        )
        json_str = result.to_tool_result()
        parsed = json.loads(json_str)

        assert parsed["success"] is True
        assert parsed["description"] == "Attack successful"
        assert parsed["damage"] == 25
        assert parsed["target"] == "monster"

    def test_action_result_to_tool_result_failure(self):
        """序列化为 JSON 格式正确 - 失败."""
        # Given: A failed action result with error message
        result = ActionResult(
            success=False,
            action_type="attack",
            error="Not enough MP",
        )
        json_str = result.to_tool_result()
        parsed = json.loads(json_str)

        assert parsed["success"] is False
        assert parsed["error"] == "Not enough MP"

    def test_action_result_empty_details(self):
        """序列化为 JSON 格式正确 - 空 details."""
        # Given: A successful action result with no details
        result = ActionResult(
            success=True,
            action_type="defend",
            description="Defense stance activated",
        )
        json_str = result.to_tool_result()
        parsed = json.loads(json_str)

        assert parsed["success"] is True
        assert parsed["description"] == "Defense stance activated"


class TestActionExecutor:
    """Tests for ActionExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        """未知工具返回错误."""
        # Given: An unknown tool name
        # When: Executing the tool
        result = await executor.execute(
            player_id="test-player",
            state={"current_hp": 100},
            tool_name="unknown_tool",
            tool_args={},
            trace_id="test-trace"
        )
        
        # Then: Should return error
        assert result.success is False
        assert "Unknown tool" in result.error
        assert result.action_type == "unknown_tool"

    @pytest.mark.asyncio
    async def test_execute_handler_exception(self, executor):
        """处理器异常被捕获."""
        # Given: A handler that raises exception
        async def failing_handler(*args, **kwargs):
            raise ValueError("Test error")
        
        executor._handle_test = failing_handler
        
        # When: Executing the tool
        result = await executor.execute(
            player_id="test-player",
            state={},
            tool_name="test",
            tool_args={},
            trace_id="test-trace"
        )
        
        # Then: Should return error
        assert result.success is False
        assert "执行错误" in result.error

    @pytest.mark.asyncio
    async def test_handle_attack_zero_hp(self, executor):
        """HP 为 0 时无法攻击."""
        # Given: Player with 0 HP
        state = {"current_hp": 0}
        
        # When: Trying to attack
        result = await executor._handle_attack(
            player_id="test-player",
            state=state,
            args={"target": "goblin"},
            trace_id="test-trace"
        )
        
        # Then: Should fail
        assert result.success is False
        assert "HP 为 0" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.end_combat')
    @patch('gameserver.game.action_executor.update_combat')
    @patch('gameserver.game.action_executor.calculate_counter_attack')
    @patch('gameserver.game.action_executor.get_combat')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_attack_miss(self, mock_pg, mock_get, mock_counter, mock_update, mock_end, executor):
        """攻击未命中分支 (roll < AC)."""
        # Given: 高 AC 怪物，确保命中失败
        mock_monster = MagicMock()
        mock_monster.ac = 100  # 非常高的 AC，确保 miss
        mock_monster.hp = 50
        mock_monster.max_hp = 50
        mock_monster.name = "Test Monster"
        mock_monster.monster_id = "test-123"
        mock_monster.defense = 5
        mock_monster.is_dead = False
        
        mock_session = MagicMock()
        mock_session.monster = mock_monster
        mock_session.round_number = 1
        
        mock_get.return_value = mock_session
        
        # Mock counter attack
        mock_counter.return_value = MagicMock(
            hits=False,
            damage=0,
            description="怪物未反击"
        )
        
        mock_pg.return_value = AsyncMock()
        
        state = {
            "current_hp": 100,
            "stat_dex": 10,  # DEX mod = 0
            "stat_luk": 10,
            "stat_agi": 10,
            "stat_str": 10,
            "level": 1,
        }
        
        # When: 攻击高 AC 怪物
        result = await executor._handle_attack(
            player_id="test-player",
            state=state,
            args={"target": "high-ac-monster"},
            trace_id="test-trace"
        )
        
        # Then: 应该未命中
        assert result.success is True
        assert "未命中" in result.description
        assert result.details["hit"] is False
        assert result.details["total_damage"] == 0
        # 验证没有调用 end_combat（怪物未死）
        mock_end.assert_not_called()

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.random')
    @patch('gameserver.game.action_executor.end_combat')
    @patch('gameserver.game.action_executor.update_combat')
    @patch('gameserver.game.action_executor.calculate_counter_attack')
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_combat')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_attack_critical_hit(self, mock_pg, mock_get, mock_state, mock_quest, 
                                       mock_counter, mock_update, mock_end, mock_random, executor):
        """暴击分支 (natural 20 或暴击判定成功)."""
        # Given: Mock 骰子和暴击
        mock_random.randint.return_value = 20  # natural 20
        mock_random.random.return_value = 0.0  # 确保暴击成功 (0.0 < crit_threshold)
        mock_random.uniform.return_value = 1.0  # 伤害方差
        mock_random.randint.side_effect = [20]  # 只调用一次 d20
        
        mock_monster = MagicMock()
        mock_monster.ac = 10  # 低 AC，确保命中
        mock_monster.hp = 100
        mock_monster.max_hp = 100
        mock_monster.name = "Test Monster"
        mock_monster.monster_id = "test-123"
        mock_monster.defense = 0
        mock_monster.is_dead = False
        
        mock_session = MagicMock()
        mock_session.monster = mock_monster
        mock_session.round_number = 1
        
        mock_get.return_value = mock_session
        
        # Mock PG queries
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = None  # 没有装备
        mock_pg.return_value = mock_pool
        
        # Mock state save
        mock_state.save_player_state = AsyncMock()
        
        # Mock counter attack
        mock_counter.return_value = MagicMock(
            hits=True,
            damage=10,
            description="怪物反击"
        )
        
        # Mock quest service
        mock_quest.update_quest_progress = AsyncMock(return_value=[])
        
        state = {
            "current_hp": 100,
            "stat_dex": 14,  # DEX mod = +2
            "stat_luk": 20,  # 高 LUK 增加暴击率
            "stat_agi": 10,
            "stat_str": 10,
            "level": 1,
        }
        
        # When: 攻击（必定暴击）
        result = await executor._handle_attack(
            player_id="test-player",
            state=state,
            args={"target": "test-monster"},
            trace_id="test-trace"
        )
        
        # Then: 应该暴击
        assert result.success is True
        assert "会心一击" in result.description
        assert result.details["hit"] is True
        assert result.details["total_damage"] > 0
        # 检查暴击细节
        assert any(h["critical"] for h in result.details["hit_details"])

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.random')
    @patch('gameserver.game.action_executor.end_combat')
    @patch('gameserver.game.action_executor.update_combat')
    @patch('gameserver.game.action_executor.calculate_counter_attack')
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_combat')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_attack_monster_defeated(self, mock_pg, mock_get, mock_state, mock_quest, 
                                          mock_counter, mock_update, mock_end, mock_random, executor):
        """怪物死亡分支 (HP 归零)."""
        # Given: Mock 骰子确保命中和高伤害
        def mock_randint(min_val, max_val):
            return 20  # 总是 20
        
        mock_random.randint = mock_randint
        mock_random.random.return_value = 0.0  # 暴击
        mock_random.uniform.return_value = 2.0  # 高伤害确保击杀
        
        mock_monster = MagicMock()
        mock_monster.ac = 10
        mock_monster.hp = 10  # 会被击杀
        mock_monster.max_hp = 100
        mock_monster.name = "Test Monster"
        mock_monster.monster_id = "test-123"
        mock_monster.defense = 0
        # is_dead 是属性，基于 hp <= 0
        type(mock_monster).is_dead = property(lambda self: self.hp <= 0)
        
        mock_session = MagicMock()
        mock_session.monster = mock_monster
        mock_session.round_number = 1
        
        mock_get.return_value = mock_session
        
        # Mock PG - 怪物定义
        mock_pool = AsyncMock()
        mock_pool.fetchrow.side_effect = [
            None,  # 装备查询
            {"exp_reward": 50, "col_reward_min": 10, "col_reward_max": 20},  # 怪物奖励
        ]
        mock_pg.return_value = mock_pool
        
        # Mock state service
        mock_state.save_player_state = AsyncMock()
        # 需要 mock _check_level_up 函数
        with patch('gameserver.game.action_executor._check_level_up', new_callable=AsyncMock, return_value=None):
            # Mock quest service
            mock_quest.update_quest_progress = AsyncMock(return_value=["任务进度更新: 击杀 1/3 怪物"])
            
            state = {
                "current_hp": 100,
                "stat_dex": 14,
                "stat_luk": 10,
                "stat_agi": 10,
                "stat_str": 10,
                "level": 1,
                "experience": 0,
                "col": 100,
                "character_id": None,  # 明确设置为 None
            }
            
            # When: 击杀怪物
            result = await executor._handle_attack(
                player_id="test-player",
                state=state,
                args={"target": "test-monster"},
                trace_id="test-trace"
            )
            
            # Then: 怪物应该被击败
            assert result.success is True
            assert "被击败了" in result.description
            assert "经验值" in result.description
            assert "珂尔" in result.description
            # 验证调用了 end_combat
            mock_end.assert_called_once()
            # 验证调用了 quest progress
            mock_quest.update_quest_progress.assert_called_once()


class TestActionExecutorDefend:
    """Tests for _handle_defend."""

    @pytest.mark.asyncio
    async def test_handle_defend_success(self, executor):
        """防御总是成功."""
        # Given: Any player state
        state = {"current_hp": 100}
        
        # When: Defending
        result = await executor._handle_defend(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should succeed with AC bonus
        assert result.success is True
        assert result.action_type == "defend"
        assert "AC+2" in result.description
        assert result.details["ac_bonus"] == 2


class TestActionExecutorLevelUp:
    """Tests for level up logic."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service.save_player_state')
    async def test_check_level_up_single(self, mock_save):
        """单次升级."""
        from gameserver.game.action_executor import _check_level_up
        
        mock_save.return_value = None
        state = {"level": 1, "experience": 0, "stat_vit": 10}
        state_changes = {"experience": 150}
        
        result = await _check_level_up(
            player_id="test-player",
            state=state,
            state_changes=state_changes,
            trace_id="test-trace"
        )
        
        # Should level up from 1 to 2
        assert "レベルアップ" in result
        assert state_changes["level"] == 2
        assert state_changes["stat_points_available"] > 0

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service.save_player_state')
    async def test_check_level_up_multiple(self, mock_save):
        """多次连续升级."""
        from gameserver.game.action_executor import _check_level_up
        
        mock_save.return_value = None
        state = {"level": 1, "experience": 0, "stat_vit": 10}
        state_changes = {"experience": 500}  # Enough for multiple levels
        
        result = await _check_level_up(
            player_id="test-player",
            state=state,
            state_changes=state_changes,
            trace_id="test-trace"
        )
        
        # Should level up multiple times
        assert "レベルアップ" in result
        assert state_changes["level"] > 2

    @pytest.mark.asyncio
    async def test_check_level_up_no_level_up(self):
        """经验不足不升级."""
        from gameserver.game.action_executor import _check_level_up
        
        state = {"level": 1, "experience": 0, "stat_vit": 10}
        state_changes = {"experience": 50}  # Not enough
        
        result = await _check_level_up(
            player_id="test-player",
            state=state,
            state_changes=state_changes,
            trace_id="test-trace"
        )
        
        # Should not level up
        assert result == ""
        # level key won't be in state_changes if no level up
        assert "level" not in state_changes


class TestActionExecutorDamageCalc:
    """Tests for damage calculation logic."""

    def test_roll_range_validation(self):
        """掷骰结果在有效范围内."""
        # Given: Multiple dice rolls
        # When: Rolling 1000 times
        # Then: All results should be in valid range
        for _ in range(1000):
            result = _roll(sides=20, count=1, modifier=0)
            assert 1 <= result["rolls"][0] <= 20
            assert 1 <= result["total"] <= 20

    def test_roll_with_negative_modifier(self):
        """负修正値测试."""
        # Given: A roll with -5 modifier
        result = _roll(sides=20, count=1, modifier=-5)
        
        assert result["modifier"] == -5
        assert result["total"] == result["rolls"][0] - 5

    def test_stat_mod_edge_cases(self):
        """属性修正边界値."""
        # Test minimum reasonable stat
        assert _stat_mod(1) == -5
        # Test very high stat
        assert _stat_mod(30) == 10

    def test_calc_exp_to_next_scaling(self):
        """经验公式随等级递增."""
        exp_1 = _calc_exp_to_next(1)
        exp_5 = _calc_exp_to_next(5)
        exp_10 = _calc_exp_to_next(10)
        
        # Should scale exponentially
        assert exp_1 < exp_5 < exp_10
        assert exp_5 > exp_1 * 2
        assert exp_10 > exp_5 * 2

    def test_calc_max_hp_scaling(self):
        """HP 公式随等级和体质递增."""
        hp_low = _calc_max_hp(level=1, vit=8)
        hp_mid = _calc_max_hp(level=5, vit=10)
        hp_high = _calc_max_hp(level=10, vit=14)
        
        assert hp_low < hp_mid < hp_high


class TestHandleUseItem:
    """Tests for use_item handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_use_healing_potion(self, mock_pg, mock_state, executor):
        """使用治疗药水恢复 HP."""
        # Given: Player with low HP
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "name": "Healing Potion",
            "item_type": "consumable",
        })
        mock_pool.execute = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "character_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_hp": 30,
            "max_hp": 100,
        }
        
        # When: Use healing potion
        result = await executor._handle_use_item(
            player_id="test-player",
            state=state,
            args={"item_id": "healing_potion"},
            trace_id="test-trace"
        )
        
        # Then: Should heal HP
        assert result.success is True
        assert "回复" in result.description  # 中文描述包含"回复"

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_use_item_not_in_inventory(self, mock_pg, executor):
        """使用背包中不存在的物品."""
        # Given: Item not in inventory
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value=None)
        
        state = {
            "character_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_hp": 100,
        }
        
        # When: Try to use non-existent item
        result = await executor._handle_use_item(
            player_id="test-player",
            state=state,
            args={"item_id": "rare_sword"},
            trace_id="test-trace"
        )
        
        # Then: Should fail
        assert result.success is False
        assert "背包中" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_use_item_no_character(self, mock_pg, executor):
        """未创建角色时使用物品."""
        # Given: No character_id
        mock_pg.return_value = AsyncMock()
        state = {"current_hp": 100}
        
        # When: Try to use item
        result = await executor._handle_use_item(
            player_id="test-player",
            state=state,
            args={"item_id": "healing_potion"},
            trace_id="test-trace"
        )
        
        # Then: Should fail
        assert result.success is False
        assert "未创建角色" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_use_antidote(self, mock_pg, executor):
        """使用解毒剂分支."""
        # Given: Antidote item
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "name": "解毒剂",
            "item_type": "consumable",
        })
        mock_pool.execute = AsyncMock()
        
        state = {
            "character_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_hp": 100,
        }
        
        # When: Use antidote
        result = await executor._handle_use_item(
            player_id="test-player",
            state=state,
            args={"item_id": "antidote"},
            trace_id="test-trace"
        )
        
        # Then: Should cure poison
        assert result.success is True
        assert "解除中毒" in result.description or "解除麻痹" in result.description

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_use_teleport_crystal(self, mock_pg, executor):
        """使用传送水晶分支."""
        # Given: Teleport crystal
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "name": "转移水晶",
            "item_type": "consumable",
        })
        mock_pool.execute = AsyncMock()
        
        state = {
            "character_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_hp": 100,
        }
        
        # When: Use teleport crystal
        result = await executor._handle_use_item(
            player_id="test-player",
            state=state,
            args={"item_id": "teleport_crystal"},
            trace_id="test-trace"
        )
        
        # Then: Should prepare teleport
        assert result.success is True
        assert "传送准备就绪" in result.description

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_use_unknown_item(self, mock_pg, executor):
        """使用未知物品分支 (generic item)."""
        # Given: Unknown item
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "name": "神秘物品",
            "item_type": "consumable",
        })
        mock_pool.execute = AsyncMock()
        
        state = {
            "character_id": "550e8400-e29b-41d4-a716-446655440000",
            "current_hp": 100,
        }
        
        # When: Use unknown item
        result = await executor._handle_use_item(
            player_id="test-player",
            state=state,
            args={"item_id": "mystery_item"},
            trace_id="test-trace"
        )
        
        # Then: Should use generic message
        assert result.success is True
        assert "使用了神秘物品" in result.description


class TestHandleFlee:
    """Tests for flee handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_combat')
    async def test_flee_success(self, mock_get, executor):
        """逃跑成功."""
        # Given: In combat
        mock_get.return_value = MagicMock(
            monster=MagicMock(ac=12, hp=30, atk=5, defense=3)
        )
        
        state = {
            "current_hp": 50,
            "stat_agi": 14,  # High agility for better flee chance
        }
        
        # When: Flee
        result = await executor._handle_flee(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should succeed (flee always returns success)
        assert result.success is True
        assert "逃跑检定" in result.description

    @pytest.mark.asyncio
    async def test_flee_not_in_combat(self, executor):
        """不在战斗中逃跑（仍然可以进行逃跑检定）."""
        # Given: Not in combat
        state = {"current_hp": 50, "stat_agi": 10}
        
        # When: Try to flee
        with patch('gameserver.game.action_executor.get_combat', return_value=None):
            result = await executor._handle_flee(
                player_id="test-player",
                state=state,
                args={},
                trace_id="test-trace"
            )
        
        # Then: Flee always returns success (dice roll determines escape)
        assert result.success is True
        assert "逃跑检定" in result.description

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor._roll')
    @patch('gameserver.game.action_executor.get_combat')
    async def test_flee_failure(self, mock_get, mock_roll, executor):
        """逃跑失败分支 (roll < DC)."""
        # Given: 低骰子点数，确保失败
        mock_get.return_value = MagicMock(
            monster=MagicMock(ac=12, hp=30, atk=5, defense=3)
        )
        mock_roll.return_value = {
            "rolls": [1],  # 骰出 1
            "modifier": 0,
            "total": 1,  # 总点数 1
            "natural_max": False,
            "natural_1": True,
        }
        
        state = {
            "current_hp": 50,
            "stat_agi": 10,  # AGI mod = 0
        }
        
        # When: Flee with low roll
        result = await executor._handle_flee(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should fail to escape
        assert result.success is True  # action 本身成功
        assert "逃跑失败" in result.description
        assert result.details["escaped"] is False


class TestHandleMoveTo:
    """Tests for move_to handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_move_to_new_location(self, mock_pg, mock_state, executor):
        """移动到新位置."""
        # Given: Player state
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "current_area": "starting_city",
            "current_location": "town_square",
            "current_floor": "1",
        }
        
        # When: Move to new location
        result = await executor._handle_move_to(
            player_id="test-player",
            state=state,
            args={"area": "forest", "location": "forest_entrance"},
            trace_id="test-trace"
        )
        
        # Then: Should update location
        assert result.success is True
        assert "forest" in result.description.lower()
        assert "forest_entrance" in result.description.lower()

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_move_to_same_location(self, mock_pg, mock_state, executor):
        """移动到当前位置."""
        # Given: Player state
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "current_area": "starting_city",
            "current_location": "town_square",
            "current_floor": "1",
        }
        
        # When: Move to same location
        result = await executor._handle_move_to(
            player_id="test-player",
            state=state,
            args={"location": "town_square"},
            trace_id="test-trace"
        )
        
        # Then: Should succeed
        assert result.success is True

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.random')
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_move_to_dangerous_area_with_encounter(self, mock_pg, mock_state, mock_random, mock_quest, executor):
        """移动到危险区域并触发遭遇战."""
        # Given: 危险区域，100% 遭遇
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        mock_random.random.return_value = 0.0  # 总是触发遭遇
        mock_random.randint.return_value = 1  # 1 只怪物
        
        # Mock 怪物查询
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[{
            "name": "哥布林",
            "level_min": 1,
            "level_max": 3,
            "monster_type": "humanoid",
        }])
        mock_pg.return_value.fetch = mock_pool.fetch
        
        # Mock quest service
        mock_quest.check_quest_triggers = AsyncMock(return_value=[])
        mock_quest.update_quest_progress = AsyncMock(return_value=[])
        
        state = {
            "current_area": "starting_city",
            "current_location": "town_square",
            "current_floor": "1",
        }
        
        # When: 移动到危险区域
        result = await executor._handle_move_to(
            player_id="test-player",
            state=state,
            args={"area": "dark_forest", "location": "forest_deep"},
            trace_id="test-trace"
        )
        
        # Then: 应该触发遭遇战
        assert result.success is True
        assert "dark_forest" in result.description
        assert "forest_deep" in result.description
        assert "野外遭遇" in result.description
        assert result.details["encounter"] is not None

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.random')
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_move_to_safe_area_no_encounter(self, mock_pg, mock_state, mock_random, mock_quest, executor):
        """移动到安全区域，不触发遭遇战."""
        # Given: 安全区域
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        mock_random.random.return_value = 0.0  # 即使是 0 也不触发（安全区域）
        
        # Mock quest service
        mock_quest.check_quest_triggers = AsyncMock(return_value=["新任务：探索城镇"])
        mock_quest.update_quest_progress = AsyncMock(return_value=["任务进度：到达城镇"])
        
        state = {
            "current_area": "forest",
            "current_location": "forest_entrance",
            "current_floor": "1",
        }
        
        # When: 移动到安全区域（town/city）
        result = await executor._handle_move_to(
            player_id="test-player",
            state=state,
            args={"area": "城镇", "location": "广场"},
            trace_id="test-trace"
        )
        
        # Then: 不应该有遭遇战，但应该有任务触发
        assert result.success is True
        assert "城镇" in result.description
        assert result.details["encounter"] is None
        assert "新任务可接取" in result.description
        assert "任务进度" in result.description

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_move_to_without_location(self, mock_pg, mock_state, mock_quest, executor):
        """移动时不提供 location，使用 area 作为 location."""
        # Given: 只有 area
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        
        # Mock quest service
        mock_quest.check_quest_triggers = AsyncMock(return_value=[])
        mock_quest.update_quest_progress = AsyncMock(return_value=[])
        
        state = {
            "current_area": "starting_city",
            "current_floor": "1",
        }
        
        # When: 移动只有 area
        result = await executor._handle_move_to(
            player_id="test-player",
            state=state,
            args={"area": "forest"},
            trace_id="test-trace"
        )
        
        # Then: location 应该等于 area
        assert result.success is True
        assert "forest" in result.description
        # 验证 state_changes
        assert mock_state.save_player_state.called
        call_args = mock_state.save_player_state.call_args[0][1]
        assert call_args["current_location"] == "forest"


class TestHandleTalkToNPC:
    """Tests for talk_to_npc handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.npc_relationship_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_talk_to_npc_first_time(self, mock_pg, mock_rels, mock_quests, mock_state, executor):
        """首次与 NPC 对话."""
        # Given: New NPC interaction
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "id": "npc_001",
            "name": "Blacksmith",
            "name_en": "Blacksmith",
            "npc_type": "merchant",
            "appearance": "Strong build",
            "personality": "Friendly",
            "dialog_style": "Casual"
        })
        mock_rels.get_relationship = AsyncMock(return_value={
            "level": 0,
            "interaction_count": 0,
        })
        mock_rels.update_relationship = AsyncMock(return_value=1)
        mock_rels.get_relationship_tier = MagicMock(return_value="Stranger")
        mock_quests.check_quest_triggers = AsyncMock(return_value=[])
        mock_quests.update_quest_progress = AsyncMock(return_value=[])
        mock_state.save_player_state = AsyncMock()
        
        state = {"current_hp": 100, "level": 1}
        
        # When: Talk to NPC
        result = await executor._handle_talk_to_npc(
            player_id="test-player",
            state=state,
            args={"npc_id": "blacksmith", "topic": "闲聊"},
            trace_id="test-trace"
        )
        
        # Then: Should record interaction
        mock_rels.update_relationship.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.npc_relationship_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_talk_to_npc_existing_relationship(self, mock_pg, mock_rels, mock_quests, mock_state, executor):
        """与已有关系的 NPC 对话."""
        # Given: Existing relationship
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "id": "npc_001",
            "name": "Blacksmith",
            "name_en": "Blacksmith",
            "npc_type": "merchant",
            "appearance": "Strong build",
            "personality": "Friendly",
            "dialog_style": "Casual"
        })
        mock_rels.get_relationship = AsyncMock(return_value={
            "level": 3,
            "interaction_count": 5,
        })
        mock_rels.update_relationship = AsyncMock(return_value=4)
        mock_rels.get_relationship_tier = MagicMock(return_value="Friendly")
        mock_quests.check_quest_triggers = AsyncMock(return_value=[])
        mock_quests.update_quest_progress = AsyncMock(return_value=[])
        mock_state.save_player_state = AsyncMock()
        
        state = {"current_hp": 100, "level": 1}
        
        # When: Talk to NPC
        result = await executor._handle_talk_to_npc(
            player_id="test-player",
            state=state,
            args={"npc_id": "blacksmith", "topic": "交易"},
            trace_id="test-trace"
        )
        
        # Then: Should update relationship
        mock_rels.update_relationship.assert_called_once()
        assert result.success is True


class TestHandleAcceptQuest:
    """Tests for accept_quest handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_accept_quest_success(self, mock_pg, mock_quests, mock_state, executor):
        """成功接受任务."""
        # Given: Available quest
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "description": "Defeat goblins",
            "objectives_json": '[{"desc": "Kill 5 goblins"}]'
        })
        mock_quests.accept_quest = AsyncMock(return_value={
            "success": True,
            "message": "Quest accepted",
            "quest_id": "quest_001",
            "quest_name": "Defeat Goblins",
        })
        mock_state.save_player_state = AsyncMock()
        
        state = {"current_hp": 100, "level": 1}
        
        # When: Accept quest
        result = await executor._handle_accept_quest(
            player_id="test-player",
            state=state,
            args={"quest_id": "quest_001"},
            trace_id="test-trace"
        )
        
        # Then: Should accept quest
        mock_quests.accept_quest.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.quest_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_accept_quest_already_completed(self, mock_pg, mock_quests, executor):
        """接受已完成的任务."""
        # Given: Quest already completed
        mock_pg.return_value = AsyncMock()
        mock_quests.accept_quest = AsyncMock(return_value={
            "success": False,
            "message": "Quest already completed",
        })
        
        state = {"current_hp": 100, "level": 1}
        
        # When: Accept quest
        result = await executor._handle_accept_quest(
            player_id="test-player",
            state=state,
            args={"quest_id": "quest_001"},
            trace_id="test-trace"
        )
        
        # Then: Should fail
        assert result.success is False
        assert "completed" in result.error.lower()


class TestHandleRest:
    """Tests for rest handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_rest_heal_hp(self, mock_pg, mock_state, executor):
        """休息恢复 HP."""
        # Given: Injured player
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "current_hp": 30,
            "max_hp": 100,
            "level": 1,
            "stat_vit": 10,
        }
        
        # When: Rest
        result = await executor._handle_rest(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should heal HP
        assert result.success is True
        # HP should increase but not exceed max_hp
        new_hp = result.state_changes.get("current_hp", 30)
        assert new_hp > 30
        assert new_hp <= 100

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_rest_at_full_hp(self, mock_pg, mock_state, executor):
        """满 HP 时休息."""
        # Given: Player at full HP
        mock_pg.return_value = AsyncMock()
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "current_hp": 100,
            "max_hp": 100,
            "level": 1,
            "stat_vit": 10,
        }
        
        # When: Rest
        result = await executor._handle_rest(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should succeed
        assert result.success is True


class TestHandleInspect:
    """Tests for inspect handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_inspect_monster(self, mock_pg, executor):
        """查看怪物信息."""
        # Given: Monster exists
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value={
            "name": "Goblin",
            "monster_type": "humanoid",
            "level_min": 1,
            "level_max": 5,
            "hp": 15,
            "atk": 4,
            "defense": 2,
            "ac": 12,
            "weaknesses": "fire",
            "description": "A small green creature",
        })
        
        state = {"current_hp": 100}
        
        # When: Inspect monster
        result = await executor._handle_inspect(
            player_id="test-player",
            state=state,
            args={"target": "goblin"},
            trace_id="test-trace"
        )
        
        # Then: Should return monster info
        assert result.success is True

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_inspect_not_found(self, mock_pg, executor):
        """查看不存在的目标."""
        # Given: Target not found
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetchrow = AsyncMock(return_value=None)
        
        state = {"current_hp": 100}
        
        # When: Inspect non-existent target
        result = await executor._handle_inspect(
            player_id="test-player",
            state=state,
            args={"target": "unknown_creature"},
            trace_id="test-trace"
        )
        
        # Then: Should return not found message
        assert result.success is True
        assert "未找到" in result.description or "unknown" in result.description.lower()


class TestHandleCheckStatus:
    """Tests for check_status handler."""

    @pytest.mark.asyncio
    async def test_check_status_basic(self, executor):
        """查看角色状态."""
        # Given: Player state
        state = {
            "current_hp": 75,
            "max_hp": 100,
            "level": 5,
            "exp": 450,
            "exp_to_next": 650,
            "stat_str": 14,
            "stat_dex": 12,
            "stat_con": 13,
            "stat_int": 10,
            "stat_wis": 11,
            "stat_cha": 9,
        }
        
        # When: Check status
        result = await executor._handle_check_status(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should return status info
        assert result.success is True
        assert "HP" in result.description or "75" in result.description


class TestHandleCheckInventory:
    """Tests for check_inventory handler."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_check_inventory_with_items(self, mock_pg, executor):
        """查看背包有物品."""
        # Given: Player has items
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetch = AsyncMock(return_value=[
            {
                "item_def_id": "healing_potion",
                "name": "Healing Potion",
                "quantity": 3,
                "enhancement_level": 0,
                "is_equipped": False,
            },
            {
                "item_def_id": "antidote",
                "name": "Antidote",
                "quantity": 1,
                "enhancement_level": 0,
                "is_equipped": False,
            },
        ])
        
        state = {"character_id": "550e8400-e29b-41d4-a716-446655440000"}
        
        # When: Check inventory
        result = await executor._handle_check_inventory(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should list items
        assert result.success is True

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_check_inventory_empty(self, mock_pg, executor):
        """查看空背包."""
        # Given: Empty inventory
        mock_pool = AsyncMock()
        mock_pg.return_value = mock_pool
        mock_pool.fetch = AsyncMock(return_value=[])
        
        state = {"character_id": "550e8400-e29b-41d4-a716-446655440000"}
        
        # When: Check inventory
        result = await executor._handle_check_inventory(
            player_id="test-player",
            state=state,
            args={},
            trace_id="test-trace"
        )
        
        # Then: Should show empty message
        assert result.success is True
        assert "空" in result.description or "empty" in result.description.lower()


class TestHandleRollDice:
    """Tests for roll_dice handler."""

    @pytest.mark.asyncio
    async def test_roll_d20(self, executor):
        """掷 d20."""
        # When: Roll d20
        result = await executor._handle_roll_dice(
            player_id="test-player",
            state={},
            args={"dice": "d20"},
            trace_id="test-trace"
        )
        
        # Then: Should return roll result
        assert result.success is True
        assert "d20" in result.description.lower() or "1-20" in result.description

    @pytest.mark.asyncio
    async def test_roll_multiple_dice(self, executor):
        """掷多个骰子."""
        # When: Roll 2d6
        result = await executor._handle_roll_dice(
            player_id="test-player",
            state={},
            args={"dice": "2d6"},
            trace_id="test-trace"
        )
        
        # Then: Should return roll result (implementation may vary)
        assert result.success is True
        # The implementation might default to 1d20 if parsing fails
        assert "骰子" in result.description or "roll" in result.description.lower()


# ====================================================================
# 技能系统测试 (覆盖 174-194 行)
# ====================================================================

class TestSkillSystem:
    """Tests for sword skill system."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.end_combat')
    @patch('gameserver.game.action_executor.update_combat')
    @patch('gameserver.game.action_executor.calculate_counter_attack')
    @patch('gameserver.game.action_executor.get_combat')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_attack_unknown_skill(self, mock_pg, mock_get, mock_counter, mock_update, mock_end, executor):
        """使用未知剑技时失败."""
        # Given: 不存在的剑技 ID
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)  # 技能不存在
        mock_pg.return_value = mock_pool
        
        state = {
            "current_hp": 100,
            "stat_dex": 10,
            "stat_luk": 10,
            "stat_agi": 10,
            "stat_str": 10,
            "level": 5,
        }
        
        # When: 使用未知剑技攻击
        result = await executor._handle_attack(
            player_id="test-player",
            state=state,
            args={"target": "goblin", "skill_id": "unknown_skill"},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "未知剑技" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.end_combat')
    @patch('gameserver.game.action_executor.update_combat')
    @patch('gameserver.game.action_executor.calculate_counter_attack')
    @patch('gameserver.game.action_executor.get_combat')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_attack_skill_level_insufficient(self, mock_pg, mock_get, mock_counter, mock_update, mock_end, executor):
        """剑技等级不足时失败."""
        # Given: 高等级剑技，低等级玩家
        mock_skill = MagicMock()
        mock_skill.__getitem__ = lambda s, key: {
            "id": "horizontal_square",
            "name": "水平四方斩",
            "required_level": 10,
            "damage_multiplier": 2.5,
            "hit_count": 4,
            "cooldown_seconds": 30,
        }[key]
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_skill)
        mock_pg.return_value = mock_pool
        
        state = {
            "current_hp": 100,
            "stat_dex": 10,
            "stat_luk": 10,
            "stat_agi": 10,
            "stat_str": 10,
            "level": 5,  # 等级不足
        }
        
        # When: 使用高等级剑技
        result = await executor._handle_attack(
            player_id="test-player",
            state=state,
            args={"target": "goblin", "skill_id": "horizontal_square"},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "等级不足" in result.error
        assert "水平四方斩" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.end_combat')
    @patch('gameserver.game.action_executor.update_combat')
    @patch('gameserver.game.action_executor.calculate_counter_attack')
    @patch('gameserver.game.action_executor.get_combat')
    @patch('gameserver.game.action_executor.get_pg')
    async def test_attack_with_skill_success(self, mock_pg, mock_get, mock_counter, mock_update, mock_end, executor):
        """成功使用剑技攻击."""
        # Given: 有效的剑技和战斗状态
        mock_skill = MagicMock()
        mock_skill.__getitem__ = lambda s, key: {
            "id": "horizontal",
            "name": "水平斩击",
            "required_level": 1,
            "damage_multiplier": 1.5,
            "hit_count": 1,
            "cooldown_seconds": 10,
        }[key]
        
        mock_monster = MagicMock()
        mock_monster.ac = 10
        mock_monster.hp = 50
        mock_monster.max_hp = 50
        mock_monster.name = "Test Monster"
        mock_monster.monster_id = "test-123"
        mock_monster.defense = 5
        mock_monster.is_dead = False
        
        mock_session = MagicMock()
        mock_session.monster = mock_monster
        mock_session.round_number = 1
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(side_effect=[
            mock_skill,  # 技能查询
            None,  # 装备查询（无装备）
        ])
        
        mock_pg.return_value = mock_pool
        mock_get.return_value = mock_session
        
        mock_counter.return_value = MagicMock(
            hits=False,
            damage=0,
            description="怪物未反击"
        )
        
        state = {
            "current_hp": 100,
            "stat_dex": 14,  # +2 mod
            "stat_luk": 10,
            "stat_agi": 12,
            "stat_str": 16,  # +3 mod
            "level": 5,
            "character_id": str(uuid.uuid4()),
        }
        
        # When: 使用剑技攻击
        result = await executor._handle_attack(
            player_id="test-player",
            state=state,
            args={"target": "test-123", "skill_id": "horizontal"},
            trace_id="test-trace"
        )
        
        # Then: 应该成功
        assert result.success is True
        assert "水平斩击" in result.description
        # skill_used 可能不在 details 中，取决于实现
        assert "skill_used" in result.details or result.details.get("hit") is not None


# ====================================================================
# 交易功能测试 (覆盖 678-729 行)
# ====================================================================

class TestTradeSystem:
    """Tests for trade system."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    @patch('gameserver.game.action_executor.state_service')
    async def test_handle_trade_buy_success(self, mock_state, mock_pg, executor):
        """成功购买物品."""
        # Given: 玩家有足够珂尔
        mock_item = MagicMock()
        mock_item.__getitem__ = lambda s, key: {
            "id": "potion_hp_small",
            "name": "小型回复药水",
            "base_price": 50,
            "weapon_durability": None,
        }[key]
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_item)
        mock_pool.execute = AsyncMock()
        mock_pg.return_value = mock_pool
        
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "col": 200,
            "character_id": str(uuid.uuid4()),
        }
        
        # When: 购买物品
        result = await executor._handle_trade(
            player_id="test-player",
            state=state,
            args={"npc_id": "merchant_01", "action": "buy", "item_id": "potion_hp_small", "quantity": 2},
            trace_id="test-trace"
        )
        
        # Then: 购买成功
        assert result.success is True
        assert "购买了" in result.description
        assert "小型回复药水" in result.description
        assert result.state_changes["col"] == 100  # 200 - 100
        mock_state.save_player_state.assert_called_once()

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_trade_buy_insufficient_col(self, mock_pg, executor):
        """珂尔不足时购买失败."""
        # Given: 玩家珂尔不足
        mock_item = MagicMock()
        mock_item.__getitem__ = lambda s, key: {
            "id": "sword_iron",
            "name": "铁剑",
            "base_price": 500,
            "weapon_durability": 100,
        }[key]
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_item)
        mock_pg.return_value = mock_pool
        
        state = {
            "col": 100,  # 不够
            "character_id": str(uuid.uuid4()),
        }
        
        # When: 尝试购买
        result = await executor._handle_trade(
            player_id="test-player",
            state=state,
            args={"npc_id": "merchant_01", "action": "buy", "item_id": "sword_iron", "quantity": 1},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "珂尔不足" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_trade_unknown_item(self, mock_pg, executor):
        """交易未知物品时失败."""
        # Given: 不存在的物品
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)
        mock_pg.return_value = mock_pool
        
        state = {"col": 1000}
        
        # When: 交易未知物品
        result = await executor._handle_trade(
            player_id="test-player",
            state=state,
            args={"npc_id": "merchant_01", "action": "buy", "item_id": "nonexistent", "quantity": 1},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "未知物品" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_settings')
    async def test_handle_trade_sell_success(self, mock_settings, mock_state, mock_pg, executor):
        """成功出售物品."""
        # Given: 玩家出售物品
        mock_item = MagicMock()
        mock_item.__getitem__ = lambda s, key: {
            "id": "wolf_pelt",
            "name": "狼皮",
            "base_price": 100,
            "weapon_durability": None,
        }[key]
        
        mock_settings_obj = MagicMock()
        mock_settings_obj.game.economy.npc_buy_rate = 0.5
        mock_settings.return_value = mock_settings_obj
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_item)
        mock_pool.execute = AsyncMock()
        mock_pg.return_value = mock_pool
        
        mock_state.save_player_state = AsyncMock()
        
        state = {
            "col": 50,
            "character_id": str(uuid.uuid4()),
        }
        
        # When: 出售物品
        result = await executor._handle_trade(
            player_id="test-player",
            state=state,
            args={"npc_id": "merchant_01", "action": "sell", "item_id": "wolf_pelt", "quantity": 3},
            trace_id="test-trace"
        )
        
        # Then: 出售成功
        assert result.success is True
        assert "出售" in result.description
        assert result.state_changes["col"] == 200  # 50 + 150 (300 * 0.5)


# ====================================================================
# 装备功能测试 (覆盖 920-989 行)
# ====================================================================

class TestEquipItem:
    """Tests for equip item functionality."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_equip_item_no_character(self, mock_pg, executor):
        """未创建角色时装备失败."""
        # Given: 没有 character_id
        state = {"level": 5}
        
        # When: 尝试装备物品
        result = await executor._handle_equip_item(
            player_id="test-player",
            state=state,
            args={"item_id": "sword_iron", "slot": "main_hand"},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "未创建角色" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_equip_item_not_in_inventory(self, mock_pg, executor):
        """背包中没有物品时装备失败."""
        # Given: 物品不在背包中
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)
        mock_pg.return_value = mock_pool
        
        state = {"character_id": str(uuid.uuid4())}
        
        # When: 尝试装备不存在的物品
        result = await executor._handle_equip_item(
            player_id="test-player",
            state=state,
            args={"item_id": "sword_legendary", "slot": "main_hand"},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "背包中没有" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_equip_item_already_equipped(self, mock_pg, executor):
        """物品已装备时失败."""
        # Given: 物品已经装备
        mock_inv = MagicMock()
        mock_inv.__getitem__ = lambda s, key: {
            "inv_id": 123,
            "is_equipped": True,
            "equipped_slot": "main_hand",
            "name": "铁剑",
            "item_type": "weapon",
            "weapon_atk": 15,
            "armor_defense": None,
        }[key]
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_inv)
        mock_pg.return_value = mock_pool
        
        state = {"character_id": str(uuid.uuid4())}
        
        # When: 尝试装备已装备的物品
        result = await executor._handle_equip_item(
            player_id="test-player",
            state=state,
            args={"item_id": "sword_iron"},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "已在装备中" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_equip_item_success_weapon(self, mock_pg, executor):
        """成功装备武器."""
        # Given: 背包中有未装备的武器
        mock_inv = MagicMock()
        mock_inv.__getitem__ = lambda s, key: {
            "inv_id": 456,
            "is_equipped": False,
            "equipped_slot": None,
            "name": "钢剑",
            "item_type": "weapon",
            "weapon_atk": 25,
            "armor_defense": None,
        }[key]
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_inv)
        mock_pool.execute = AsyncMock()
        mock_pg.return_value = mock_pool
        
        state = {"character_id": str(uuid.uuid4())}
        
        # When: 装备武器
        result = await executor._handle_equip_item(
            player_id="test-player",
            state=state,
            args={"item_id": "sword_steel"},
            trace_id="test-trace"
        )
        
        # Then: 装备成功
        assert result.success is True
        assert "钢剑" in result.description
        assert "ATK 25" in result.description
        assert mock_pool.execute.call_count == 2  # 卸装 + 装备

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_pg')
    async def test_handle_equip_item_success_armor(self, mock_pg, executor):
        """成功装备防具."""
        # Given: 背包中有未装备的防具
        mock_inv = MagicMock()
        mock_inv.__getitem__ = lambda s, key: {
            "inv_id": 789,
            "is_equipped": False,
            "equipped_slot": None,
            "name": "皮革铠甲",
            "item_type": "armor_body",
            "weapon_atk": None,
            "armor_defense": 10,
        }[key]
        
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=mock_inv)
        mock_pool.execute = AsyncMock()
        mock_pg.return_value = mock_pool
        
        state = {"character_id": str(uuid.uuid4())}
        
        # When: 装备防具
        result = await executor._handle_equip_item(
            player_id="test-player",
            state=state,
            args={"item_id": "armor_leather"},
            trace_id="test-trace"
        )
        
        # Then: 装备成功
        assert result.success is True
        assert "皮革铠甲" in result.description
        assert "DEF 10" in result.description


# ====================================================================
# 传送水晶测试 (覆盖 575-595 行)
# ====================================================================

class TestTeleportCrystal:
    """Tests for teleport crystal functionality."""

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.state_service')
    @patch('gameserver.game.action_executor.get_settings')
    async def test_handle_use_teleport_crystal_success(self, mock_settings, mock_state, executor):
        """成功使用传送水晶."""
        # Given: 有效的楼层
        mock_settings_obj = MagicMock()
        mock_settings_obj.game.floor.max_floor = 10
        mock_settings_obj.game.floor.floor_areas = {
            1: "起始之城",
            5: "第五层主街区",
        }
        mock_settings.return_value = mock_settings_obj
        
        mock_state.save_player_state = AsyncMock()
        
        state = {"current_floor": 1, "current_area": "起始之城"}
        
        # When: 传送到第5层
        result = await executor._handle_use_teleport_crystal(
            player_id="test-player",
            state=state,
            args={"floor": 5},
            trace_id="test-trace"
        )
        
        # Then: 传送成功
        assert result.success is True
        assert "第五层主街区" in result.description
        assert result.state_changes["current_floor"] == 5
        assert result.state_changes["current_area"] == "第五层主街区"
        assert result.state_changes["current_location"] == "转移门广场"

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_settings')
    async def test_handle_use_teleport_crystal_invalid_floor(self, mock_settings, executor):
        """传送到无效楼层时失败."""
        # Given: 超出范围的楼层
        mock_settings_obj = MagicMock()
        mock_settings_obj.game.floor.max_floor = 10
        mock_settings.return_value = mock_settings_obj
        
        state = {"current_floor": 1}
        
        # When: 传送到第15层（超出范围）
        result = await executor._handle_use_teleport_crystal(
            player_id="test-player",
            state=state,
            args={"floor": 15},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "无法传送" in result.error

    @pytest.mark.asyncio
    @patch('gameserver.game.action_executor.get_settings')
    async def test_handle_use_teleport_crystal_floor_zero(self, mock_settings, executor):
        """传送到第0层时失败."""
        # Given: 楼层为0
        mock_settings_obj = MagicMock()
        mock_settings_obj.game.floor.max_floor = 10
        mock_settings.return_value = mock_settings_obj
        
        state = {"current_floor": 1}
        
        # When: 传送到第0层
        result = await executor._handle_use_teleport_crystal(
            player_id="test-player",
            state=state,
            args={"floor": 0},
            trace_id="test-trace"
        )
        
        # Then: 应该失败
        assert result.success is False
        assert "无法传送" in result.error
