"""Tests for context_builder module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gameserver.game.context_builder import (
    GameContext,
    _format_state_snapshot,
    build_context,
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
