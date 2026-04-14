"""Tests for action_executor module."""

import json
import pytest

from gameserver.game.action_executor import (
    ActionResult,
    _roll,
    _stat_mod,
    _calc_exp_to_next,
    _calc_max_hp,
)


class TestRoll:
    """Tests for dice rolling functions."""

    def test_roll_basic(self):
        """单次掷骰返回格式正确、范围在 1-20."""
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
        result = _roll(sides=20, count=1, modifier=5)

        assert result["modifier"] == 5
        assert result["total"] == result["rolls"][0] + 5

    def test_roll_multiple_dice(self):
        """多骰子掷骰."""
        result = _roll(sides=6, count=3, modifier=0)

        assert len(result["rolls"]) == 3
        for roll in result["rolls"]:
            assert 1 <= roll <= 6
        assert result["total"] == sum(result["rolls"])

    def test_roll_natural_max(self):
        """natural_max 为 True 当掷出最大值."""
        # Mock by testing many rolls
        found_max = False
        for _ in range(100):
            result = _roll(sides=20, count=1, modifier=0)
            if result["rolls"][0] == 20:
                found_max = True
                assert result["natural_max"] is True
                break
        # Just verify the logic works (we should hit 20 eventually)
        # This test is probabilistic but very likely to pass

    def test_roll_natural_1(self):
        """natural_1 为 True 当掷出 1."""
        found_1 = False
        for _ in range(100):
            result = _roll(sides=20, count=1, modifier=0)
            if result["rolls"][0] == 1:
                found_1 = True
                assert result["natural_1"] is True
                break


class TestStatMod:
    """Tests for stat modifier calculation."""

    def test_stat_mod_calculation_10(self):
        """属性值 10→0."""
        assert _stat_mod(10) == 0

    def test_stat_mod_calculation_16(self):
        """属性值 16→+3."""
        assert _stat_mod(16) == 3

    def test_stat_mod_calculation_8(self):
        """属性值 8→-1."""
        assert _stat_mod(8) == -1

    def test_stat_mod_calculation_12(self):
        """属性值 12→+1."""
        assert _stat_mod(12) == 1

    def test_stat_mod_calculation_14(self):
        """属性值 14→+2."""
        assert _stat_mod(14) == 2

    def test_stat_mod_calculation_20(self):
        """属性值 20→+5."""
        assert _stat_mod(20) == 5

    def test_stat_mod_calculation_4(self):
        """属性值 4→-3."""
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
        result = ActionResult(
            success=True,
            action_type="defend",
            description="Defense stance activated",
        )
        json_str = result.to_tool_result()
        parsed = json.loads(json_str)

        assert parsed["success"] is True
        assert parsed["description"] == "Defense stance activated"
