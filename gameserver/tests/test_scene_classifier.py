"""Tests for scene_classifier module."""

import pytest

from gameserver.game.scene_classifier import (
    SceneType,
    classify_scene,
    TOOL_GROUPS,
    prune_tools,
    get_rag_entity_type,
)


class TestClassifyCombatScene:
    """Tests for combat scene classification."""

    def test_classify_combat_scene_with_attack_keyword(self):
        """包含攻击关键词 → COMBAT."""
        # Given: 包含攻击关键词的消息
        message = "我要攻击那只野狼"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 COMBAT 类型
        assert scene == SceneType.COMBAT

    def test_classify_combat_scene_with_battle_keyword(self):
        """包含战斗关键词 → COMBAT."""
        # Given: 包含战斗关键词的消息
        message = "准备战斗！"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 COMBAT 类型
        assert scene == SceneType.COMBAT

    def test_classify_combat_scene_with_skill_keyword(self):
        """包含剑技关键词 → COMBAT."""
        # Given: 包含剑技关键词的消息
        message = "使用剑技攻击"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 COMBAT 类型
        assert scene == SceneType.COMBAT


class TestClassifyExplorationScene:
    """Tests for exploration scene classification."""

    def test_classify_exploration_scene_with_move_keyword(self):
        """包含移动关键词 → EXPLORATION."""
        # Given: 包含移动关键词的消息
        message = "移动到起始之城"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 EXPLORATION 类型
        assert scene == SceneType.EXPLORATION

    def test_classify_exploration_scene_with_explore_keyword(self):
        """包含探索关键词 → EXPLORATION."""
        # Given: 包含探索关键词的消息
        message = "探索迷宫"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 EXPLORATION 类型
        assert scene == SceneType.EXPLORATION

    def test_classify_exploration_scene_with_enter_keyword(self):
        """包含进入关键词 → EXPLORATION."""
        # Given: 包含进入关键词的消息
        message = "进入地下城"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 EXPLORATION 类型
        assert scene == SceneType.EXPLORATION


class TestClassifySocialScene:
    """Tests for social scene classification."""

    def test_classify_social_scene_with_talk_keyword(self):
        """包含对话关键词 → SOCIAL."""
        # Given: 包含对话关键词的消息
        message = "与NPC对话"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 SOCIAL 类型
        assert scene == SceneType.SOCIAL

    def test_classify_social_scene_with_trade_keyword(self):
        """包含交易关键词 → SOCIAL."""
        # Given: 包含交易关键词的消息
        message = "购买物品"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 SOCIAL 类型
        assert scene == SceneType.SOCIAL


class TestClassifyRestScene:
    """Tests for rest scene classification."""

    def test_classify_rest_scene_with_rest_keyword(self):
        """包含休息关键词 → REST."""
        # Given: 包含休息关键词的消息
        message = "去旅馆休息"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 REST 类型
        assert scene == SceneType.REST


class TestClassifyGeneralScene:
    """Tests for general scene classification."""

    def test_classify_general_scene_when_no_keywords_match(self):
        """没有匹配关键词时 → GENERAL."""
        # Given: 不包含任何特定关键词的消息
        message = "你好，今天天气不错"

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 GENERAL 类型
        assert scene == SceneType.GENERAL

    def test_classify_general_scene_with_empty_message(self):
        """空消息时 → GENERAL."""
        # Given: 空消息
        message = ""

        # When: 分类场景
        scene = classify_scene(message)

        # Then: 返回 GENERAL 类型
        assert scene == SceneType.GENERAL


class TestToolGroupsMapping:
    """Tests for TOOL_GROUPS mapping."""

    def test_tool_groups_mapping_combat_not_empty(self):
        """COMBAT 场景工具组非空."""
        # Given: COMBAT 场景类型
        scene = SceneType.COMBAT

        # When: 获取工具组
        tools = TOOL_GROUPS.get(scene)

        # Then: 工具组非空
        assert tools is not None
        assert len(tools) > 0
        assert "attack" in tools
        assert "defend" in tools

    def test_tool_groups_mapping_exploration_not_empty(self):
        """EXPLORATION 场景工具组非空."""
        # Given: EXPLORATION 场景类型
        scene = SceneType.EXPLORATION

        # When: 获取工具组
        tools = TOOL_GROUPS.get(scene)

        # Then: 工具组非空
        assert tools is not None
        assert len(tools) > 0
        assert "move_to" in tools
        assert "enter_dungeon" in tools

    def test_tool_groups_mapping_social_not_empty(self):
        """SOCIAL 场景工具组非空."""
        # Given: SOCIAL 场景类型
        scene = SceneType.SOCIAL

        # When: 获取工具组
        tools = TOOL_GROUPS.get(scene)

        # Then: 工具组非空
        assert tools is not None
        assert len(tools) > 0
        assert "talk_to_npc" in tools
        assert "trade" in tools

    def test_tool_groups_mapping_rest_not_empty(self):
        """REST 场景工具组非空."""
        # Given: REST 场景类型
        scene = SceneType.REST

        # When: 获取工具组
        tools = TOOL_GROUPS.get(scene)

        # Then: 工具组非空
        assert tools is not None
        assert len(tools) > 0
        assert "rest" in tools


class TestPruneTools:
    """Tests for prune_tools function."""

    def test_prune_tools_returns_all_for_general(self):
        """GENERAL 场景返回所有工具."""
        # Given: 所有工具和 GENERAL 场景
        all_tools = [
            {"function": {"name": "attack"}},
            {"function": {"name": "move_to"}},
            {"function": {"name": "talk_to_npc"}},
        ]

        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.GENERAL)

        # Then: 返回所有工具
        assert len(pruned) == 3

    def test_prune_tools_filters_by_scene(self):
        """根据场景类型过滤工具."""
        # Given: 所有工具和 COMBAT 场景
        all_tools = [
            {"function": {"name": "attack"}},
            {"function": {"name": "move_to"}},
            {"function": {"name": "talk_to_npc"}},
        ]

        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.COMBAT)

        # Then: 只返回 COMBAT 相关工具
        assert len(pruned) == 1
        assert pruned[0]["function"]["name"] == "attack"


class TestGetRagEntityType:
    """Tests for get_rag_entity_type function."""

    def test_get_rag_entity_type_combat_returns_monster(self):
        """COMBAT 场景返回 monster."""
        entity_type = get_rag_entity_type(SceneType.COMBAT)
        assert entity_type == "monster"

    def test_get_rag_entity_type_social_returns_npc(self):
        """SOCIAL 场景返回 npc."""
        entity_type = get_rag_entity_type(SceneType.SOCIAL)
        assert entity_type == "npc"

    def test_get_rag_entity_type_exploration_returns_none(self):
        """EXPLORATION 场景返回 None."""
        entity_type = get_rag_entity_type(SceneType.EXPLORATION)
        assert entity_type is None
