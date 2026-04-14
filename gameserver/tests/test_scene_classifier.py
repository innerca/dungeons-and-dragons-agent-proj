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

    def test_get_rag_entity_type_rest_returns_none(self):
        """REST 场景返回 None."""
        entity_type = get_rag_entity_type(SceneType.REST)
        assert entity_type is None

    def test_get_rag_entity_type_general_returns_none(self):
        """GENERAL 场景返回 None."""
        entity_type = get_rag_entity_type(SceneType.GENERAL)
        assert entity_type is None


class TestClassifySceneEdgeCases:
    """Tests for classify_scene edge cases."""

    def test_classify_scene_case_insensitive(self):
        """关键词匹配不区分大小写."""
        # Given: 大写关键词
        message = "我要攻击 BOSS"
        
        # When: 分类场景
        scene = classify_scene(message)
        
        # Then: 应该识别为 COMBAT
        assert scene == SceneType.COMBAT

    def test_classify_scene_multiple_keywords(self):
        """多个关键词匹配时选择分数最高的."""
        # Given: 同时包含 combat 和 social 关键词
        message = "攻击怪物并购买情报"
        
        # When: 分类场景
        scene = classify_scene(message)
        
        # Then: 应该选择分数更高的（combat: 2个词 vs social: 1个词）
        assert scene == SceneType.COMBAT

    def test_classify_scene_with_custom_keywords(self):
        """使用自定义关键词映射."""
        # Given: 自定义关键词
        custom_keywords = {
            "combat": ["fight", "battle"],
            "social": ["chat", "talk"],
        }
        message = "Let's fight"
        
        # When: 分类场景
        scene = classify_scene(message, scene_keywords=custom_keywords)
        
        # Then: 应该使用自定义关键词
        assert scene == SceneType.COMBAT

    def test_classify_scene_partial_keyword_match(self):
        """部分关键词匹配."""
        # Given: 只包含一个 combat 关键词
        message = "我准备战斗"
        
        # When: 分类场景
        scene = classify_scene(message)
        
        # Then: 应该识别为 COMBAT
        assert scene == SceneType.COMBAT

    def test_classify_scene_no_match_returns_general(self):
        """没有匹配时返回 GENERAL."""
        # Given: 无关消息
        message = "今天天气真好"
        
        # When: 分类场景
        scene = classify_scene(message)
        
        # Then: 返回 GENERAL
        assert scene == SceneType.GENERAL


class TestPruneToolsEdgeCases:
    """Tests for prune_tools edge cases."""

    def test_prune_tools_empty_list(self):
        """空工具列表返回空."""
        # Given: 空工具列表
        all_tools = []
        
        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.COMBAT)
        
        # Then: 返回空列表
        assert pruned == []

    def test_prune_tools_no_match(self):
        """没有匹配的工具时返回空."""
        # Given: 工具列表不包含场景相关工具
        all_tools = [
            {"function": {"name": "unknown_tool"}},
        ]
        
        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.COMBAT)
        
        # Then: 返回空列表
        assert pruned == []

    def test_prune_tools_all_match(self):
        """所有工具都匹配时全部返回."""
        # Given: 所有工具都属于 COMBAT 场景
        all_tools = [
            {"function": {"name": "attack"}},
            {"function": {"name": "defend"}},
        ]
        
        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.COMBAT)
        
        # Then: 返回所有工具
        assert len(pruned) == 2

    def test_prune_tools_exploration_scene(self):
        """EXPLORATION 场景裁剪正确."""
        # Given: 混合工具列表
        all_tools = [
            {"function": {"name": "move_to"}},
            {"function": {"name": "attack"}},
            {"function": {"name": "enter_dungeon"}},
        ]
        
        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.EXPLORATION)
        
        # Then: 只返回 exploration 相关工具
        assert len(pruned) == 2
        tool_names = {t["function"]["name"] for t in pruned}
        assert "move_to" in tool_names
        assert "enter_dungeon" in tool_names
        assert "attack" not in tool_names

    def test_prune_tools_social_scene(self):
        """SOCIAL 场景裁剪正确."""
        # Given: 混合工具列表
        all_tools = [
            {"function": {"name": "talk_to_npc"}},
            {"function": {"name": "attack"}},
            {"function": {"name": "trade"}},
        ]
        
        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.SOCIAL)
        
        # Then: 只返回 social 相关工具
        assert len(pruned) == 2
        tool_names = {t["function"]["name"] for t in pruned}
        assert "talk_to_npc" in tool_names
        assert "trade" in tool_names
        assert "attack" not in tool_names

    def test_prune_tools_rest_scene(self):
        """REST 场景裁剪正确."""
        # Given: 混合工具列表
        all_tools = [
            {"function": {"name": "rest"}},
            {"function": {"name": "attack"}},
            {"function": {"name": "use_item"}},
        ]
        
        # When: 裁剪工具
        pruned = prune_tools(all_tools, SceneType.REST)
        
        # Then: 只返回 rest 相关工具
        assert len(pruned) == 2
        tool_names = {t["function"]["name"] for t in pruned}
        assert "rest" in tool_names
        assert "use_item" in tool_names
        assert "attack" not in tool_names


class TestToolGroupsCompleteness:
    """Tests for TOOL_GROUPS completeness."""

    def test_all_scenes_have_tool_groups(self):
        """所有场景类型都有工具组定义."""
        # Given: 所有场景类型
        scenes = [SceneType.COMBAT, SceneType.EXPLORATION, SceneType.SOCIAL, SceneType.REST]
        
        # Then: 都应该有工具组
        for scene in scenes:
            assert scene in TOOL_GROUPS, f"{scene} 没有定义工具组"
            assert len(TOOL_GROUPS[scene]) > 0, f"{scene} 的工具组为空"

    def test_common_tools_in_all_groups(self):
        """通用工具在所有场景中都可用."""
        # Given: 通用工具
        common_tools = {"check_status", "check_inventory"}
        
        # Then: 应该在所有场景工具组中
        for scene, tools in TOOL_GROUPS.items():
            for tool in common_tools:
                assert tool in tools, f"{tool} 不在 {scene} 的工具组中"

    def test_scene_specific_tools_not_shared(self):
        """场景专属工具不应该出现在其他场景."""
        # combat 专属工具不应该在 social 中
        assert "attack" not in TOOL_GROUPS[SceneType.SOCIAL]
        # social 专属工具不应该在 combat 中
        assert "talk_to_npc" not in TOOL_GROUPS[SceneType.COMBAT]
        # exploration 专属工具不应该在 rest 中
        assert "move_to" not in TOOL_GROUPS[SceneType.REST]
