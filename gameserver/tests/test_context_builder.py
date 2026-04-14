"""Tests for context_builder module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gameserver.game.context_builder import (
    GameContext,
    _format_state_snapshot,
    _format_combat_snapshot,
    _format_quest_snapshot,
    _format_relationship_snapshot,
    build_context,
    SYSTEM_PROMPT,
    FIRST_MESSAGE_GUIDE,
)


class TestFormatStateSnapshot:
    """Tests for _format_state_snapshot function."""

    def test_format_state_snapshot_includes_key_fields(self):
        """格式化输出包含关键字段."""
        # Given: 完整的玩家状态
        state = {
            "name": "TestPlayer",
            "level": 5,
            "current_hp": 150,
            "max_hp": 200,
            "col": 1000,
            "stat_str": 12,
            "stat_agi": 14,
            "stat_vit": 10,
            "stat_int": 8,
            "stat_dex": 16,
            "stat_luk": 10,
            "current_floor": 1,
            "current_area": "起始之城",
            "current_location": "中央广场",
        }

        # When: 格式化状态快照
        snapshot = _format_state_snapshot(state)

        # Then: 输出包含关键字段
        assert "TestPlayer" in snapshot
        assert "Lv.5" in snapshot
        assert "HP 150/200" in snapshot
        assert "Col 1000" in snapshot
        assert "STR 12" in snapshot
        assert "AGI 14" in snapshot
        assert "第1层" in snapshot
        assert "起始之城" in snapshot

    def test_format_state_snapshot_handles_empty_state(self):
        """空状态返回未创建角色提示."""
        # Given: 空状态
        state = {}

        # When: 格式化状态快照
        snapshot = _format_state_snapshot(state)

        # Then: 返回未创建角色提示
        assert "未创建角色" in snapshot

    def test_format_state_snapshot_handles_none_state(self):
        """None 状态返回未创建角色提示."""
        # Given: None 状态
        state = None

        # When: 格式化状态快照
        snapshot = _format_state_snapshot(state)

        # Then: 返回未创建角色提示
        assert "未创建角色" in snapshot

    def test_format_state_snapshot_uses_defaults_for_missing_fields(self):
        """缺失字段使用默认值."""
        # Given: 不完整的玩家状态
        state = {
            "name": "TestPlayer",
        }

        # When: 格式化状态快照
        snapshot = _format_state_snapshot(state)

        # Then: 使用默认值填充缺失字段
        assert "TestPlayer" in snapshot
        assert "Lv.1" in snapshot  # 默认等级
        assert "HP ?/?" in snapshot  # 默认 HP
        assert "Col 0" in snapshot  # 默认 Col


class TestGameContext:
    """Tests for GameContext dataclass."""

    def test_game_context_add_tool_result_appends_message(self):
        """添加工具结果后消息列表正确."""
        # Given: 空的 GameContext
        ctx = GameContext()

        # When: 添加工具结果
        ctx.add_tool_result("tool_call_001", {"success": True, "damage": 25})

        # Then: 消息列表包含工具结果
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "tool"
        assert ctx.messages[0]["tool_call_id"] == "tool_call_001"
        assert "success" in ctx.messages[0]["content"]

    def test_game_context_add_tool_result_multiple_times(self):
        """多次添加工具结果后消息列表正确."""
        # Given: 空的 GameContext
        ctx = GameContext()

        # When: 添加多个工具结果
        ctx.add_tool_result("tool_call_001", {"success": True})
        ctx.add_tool_result("tool_call_002", {"success": False, "error": "Failed"})

        # Then: 消息列表包含所有工具结果
        assert len(ctx.messages) == 2
        assert ctx.messages[0]["tool_call_id"] == "tool_call_001"
        assert ctx.messages[1]["tool_call_id"] == "tool_call_002"


class TestBuildContext:
    """Tests for build_context function."""

    @pytest.mark.asyncio
    async def test_build_context_includes_system_prompt(self, player_id):
        """构建的上下文包含系统提示."""
        # Given: 模拟 state_service 函数
        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={
                "name": "TestPlayer",
                "level": 5,
                "current_hp": 150,
                "max_hp": 200,
                "col": 1000,
            })
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])

            # When: 构建上下文
            ctx = await build_context(
                player_id=player_id,
                user_message="Hello",
                tools=[],
            )

        # Then: 包含系统提示
        assert len(ctx.messages) >= 2  # system + user
        assert ctx.messages[0]["role"] == "system"
        assert "地下城主" in ctx.messages[0]["content"] or "Dungeon Master" in ctx.messages[0]["content"]

    @pytest.mark.asyncio
    async def test_build_context_includes_user_message(self, player_id):
        """构建的上下文包含用户消息."""
        # Given: 模拟 state_service 函数
        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={
                "name": "TestPlayer",
                "level": 5,
                "current_hp": 150,
                "max_hp": 200,
                "col": 1000,
            })
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])

            # When: 构建上下文
            ctx = await build_context(
                player_id=player_id,
                user_message="Attack the wolf",
                tools=[],
            )

        # Then: 最后一条消息是用户消息
        assert ctx.messages[-1]["role"] == "user"
        assert ctx.messages[-1]["content"] == "Attack the wolf"

    @pytest.mark.asyncio
    async def test_build_context_includes_first_message_guide_for_new_players(self, player_id):
        """新玩家构建的上下文包含首次消息引导."""
        # Given: 模拟 state_service 函数
        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={
                "name": "TestPlayer",
                "level": 1,
                "current_hp": 200,
                "max_hp": 200,
                "col": 500,
            })
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])

            # When: 构建上下文（标记为首次消息）
            ctx = await build_context(
                player_id=player_id,
                user_message="Hello",
                tools=[],
                is_first_message=True,
            )

        # Then: 包含首次消息引导
        system_messages = [m for m in ctx.messages if m["role"] == "system"]
        assert len(system_messages) >= 2  # 系统提示 + 首次消息引导

    @pytest.mark.asyncio
    async def test_build_context_includes_tools(self, player_id):
        """构建的上下文包含工具定义."""
        # Given: 模拟 state_service 函数和工具列表
        tools = [
            {"function": {"name": "attack"}},
            {"function": {"name": "defend"}},
        ]

        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={
                "name": "TestPlayer",
                "level": 5,
                "current_hp": 150,
                "max_hp": 200,
                "col": 1000,
            })
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])

            # When: 构建上下文
            ctx = await build_context(
                player_id=player_id,
                user_message="Attack",
                tools=tools,
            )

        # Then: 上下文包含工具
        assert ctx.tools == tools

    @pytest.mark.asyncio
    async def test_build_context_includes_history(self, player_id):
        """构建的上下文包含历史消息."""
        # Given: 模拟 state_service 函数和历史消息
        history = [
            {"role": "user", "content": "Previous message 1"},
            {"role": "assistant", "content": "Previous response 1"},
        ]

        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={
                "name": "TestPlayer",
                "level": 5,
                "current_hp": 150,
                "max_hp": 200,
                "col": 1000,
            })
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=history)

            # When: 构建上下文
            ctx = await build_context(
                player_id=player_id,
                user_message="Current message",
                tools=[],
            )

        # Then: 上下文包含历史消息
        user_messages = [m for m in ctx.messages if m["role"] == "user"]
        assert len(user_messages) == 2  # Previous + Current
        assert user_messages[0]["content"] == "Previous message 1"
        assert user_messages[1]["content"] == "Current message"


class TestCombatSnapshot:
    """Tests for _format_combat_snapshot."""

    @pytest.mark.asyncio
    @patch('gameserver.game.combat_state.get_combat')
    async def test_format_combat_snapshot_with_active_combat(self, mock_get_combat):
        """战斗中有怪物时格式化正确."""
        # Given: Active combat session
        from gameserver.game.combat_state import CombatSession, MonsterState
        
        monster = MonsterState(
            monster_id="goblin_001",
            name="Goblin",
            hp=20,
            max_hp=30,
            atk=8,
            defense=3,
            ac=12,
        )
        session = CombatSession(
            player_id="test-player",
            monster=monster,
            round_number=2,
        )
        mock_get_combat.return_value = session
        
        # When: Format combat snapshot
        result = await _format_combat_snapshot("test-player")
        
        # Then: Should include monster info
        assert result is not None
        assert "Goblin" in result
        assert "HP 20/30" in result
        assert "回合 2" in result

    @pytest.mark.asyncio
    @patch('gameserver.game.combat_state.get_combat')
    async def test_format_combat_snapshot_no_combat(self, mock_get_combat):
        """没有战斗时返回 None."""
        mock_get_combat.return_value = None
        
        result = await _format_combat_snapshot("test-player")
        
        assert result is None


class TestQuestSnapshot:
    """Tests for _format_quest_snapshot."""

    @pytest.mark.asyncio
    @patch('gameserver.game.quest_service.get_active_quests')
    async def test_format_quest_snapshot_with_quests(self, mock_get_quests):
        """有活跃任务时格式化正确."""
        # Given: Active quests
        mock_get_quests.return_value = [
            {
                "name": "击败哥布林",
                "quest_type": "kill",
                "status": "active",
                "progress": {"obj1": {"completed": True}},
                "objectives": ["obj1", "obj2"],
            },
            {
                "name": "收集草药",
                "quest_type": "collect",
                "status": "available",
                "progress": {},
                "objectives": [],
            },
        ]
        
        # When: Format quest snapshot
        result = await _format_quest_snapshot("test-player")
        
        # Then: Should include quest info
        assert result is not None
        assert "活跃任务" in result
        assert "击败哥布林" in result
        assert "收集草药" in result
        assert "(1/2)" in result  # Progress

    @pytest.mark.asyncio
    @patch('gameserver.game.quest_service.get_active_quests')
    async def test_format_quest_snapshot_no_quests(self, mock_get_quests):
        """没有任务时返回 None."""
        mock_get_quests.return_value = []
        
        result = await _format_quest_snapshot("test-player")
        
        assert result is None


class TestRelationshipSnapshot:
    """Tests for _format_relationship_snapshot."""

    @pytest.mark.asyncio
    @patch('gameserver.game.npc_relationship_service.get_all_relationships')
    @patch('gameserver.game.npc_relationship_service.get_relationship_tier')
    async def test_format_relationship_snapshot_with_relationships(self, mock_tier, mock_rels):
        """有 NPC 关系时格式化正确."""
        # Given: Active relationships
        mock_rels.return_value = [
            {"npc_name": "Asuna", "level": 5, "interaction_count": 10},
            {"npc_name": "Klein", "level": 3, "interaction_count": 5},
        ]
        mock_tier.side_effect = ["友好", "认识"]
        
        # When: Format relationship snapshot
        result = await _format_relationship_snapshot("test-player")
        
        # Then: Should include relationship info
        assert result is not None
        assert "NPC关系" in result
        assert "Asuna" in result
        assert "Klein" in result

    @pytest.mark.asyncio
    @patch('gameserver.game.npc_relationship_service.get_all_relationships')
    async def test_format_relationship_snapshot_no_relationships(self, mock_rels):
        """没有关系时返回 None."""
        mock_rels.return_value = []
        
        result = await _format_relationship_snapshot("test-player")
        
        assert result is None

    @pytest.mark.asyncio
    @patch('gameserver.game.npc_relationship_service.get_all_relationships')
    async def test_format_relationship_snapshot_inactive_only(self, mock_rels):
        """只有未互动的关系时返回 None."""
        mock_rels.return_value = [
            {"npc_name": "NPC", "level": 0, "interaction_count": 0},
        ]
        
        result = await _format_relationship_snapshot("test-player")
        
        assert result is None


class TestBuildContextEdgeCases:
    """Tests for build_context edge cases."""

    @pytest.mark.asyncio
    async def test_build_context_with_rag_chunks(self, player_id):
        """构建的上下文包含 RAG 检索结果."""
        rag_chunks = [
            "艾恩葛朗特第1层是起始区域",
            "起始之城有安全的防犯罪指令",
        ]
        
        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={"name": "TestPlayer", "level": 1})
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])
            
            ctx = await build_context(
                player_id=player_id,
                user_message="Hello",
                tools=[],
                rag_chunks=rag_chunks,
            )
        
        # Then: Should include RAG content
        system_messages = [m for m in ctx.messages if m["role"] == "system"]
        rag_messages = [m for m in system_messages if "世界知识参考" in m["content"]]
        assert len(rag_messages) == 1
        assert "艾恩葛朗特" in rag_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_build_context_with_summary(self, player_id):
        """构建的上下文包含历史摘要."""
        summary = "玩家在第1层击败了10只哥布林"
        
        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={"name": "TestPlayer", "level": 1})
            mock_state_service.get_summary = AsyncMock(return_value=summary)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])
            
            ctx = await build_context(
                player_id=player_id,
                user_message="Hello",
                tools=[],
            )
        
        # Then: Should include summary
        system_messages = [m for m in ctx.messages if m["role"] == "system"]
        summary_messages = [m for m in system_messages if "冒险经历摘要" in m["content"]]
        assert len(summary_messages) == 1
        assert "哥布林" in summary_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_build_context_token_estimation(self, player_id):
        """构建上下文时计算 token 估算."""
        with patch("gameserver.game.context_builder.state_service") as mock_state_service:
            mock_state_service.load_player_state = AsyncMock(return_value={"name": "TestPlayer", "level": 1})
            mock_state_service.get_summary = AsyncMock(return_value=None)
            mock_state_service.get_recent_messages = AsyncMock(return_value=[])
            
            # Should not raise any errors
            ctx = await build_context(
                player_id=player_id,
                user_message="Hello",
                tools=[],
                trace_id="test-trace",
            )
        
        # Context should be built successfully
        assert ctx is not None
        assert len(ctx.messages) > 0


class TestSystemPrompts:
    """Tests for system prompt constants."""

    def test_system_prompt_contains_key_elements(self):
        """系统提示包含关键元素."""
        assert "地下城主" in SYSTEM_PROMPT or "Dungeon Master" in SYSTEM_PROMPT
        assert "艾恩葛朗特" in SYSTEM_PROMPT
        assert "死亡" in SYSTEM_PROMPT
        assert "工具" in SYSTEM_PROMPT or "tool" in SYSTEM_PROMPT.lower()

    def test_first_message_guide_contains_key_elements(self):
        """首次消息引导包含关键元素."""
        assert "欢迎" in FIRST_MESSAGE_GUIDE or "第一次" in FIRST_MESSAGE_GUIDE
        assert "艾恩葛朗特" in FIRST_MESSAGE_GUIDE
        assert "死亡" in FIRST_MESSAGE_GUIDE
        assert "起始之城" in FIRST_MESSAGE_GUIDE
