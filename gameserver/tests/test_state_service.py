"""Tests for state_service module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gameserver.db import state_service


class TestKeyHelpers:
    """Tests for Redis key helper functions."""

    def test_state_key_format(self):
        """状态 key 格式正确."""
        key = state_service._state_key("test-player-123")
        assert key == "sao:player:test-player-123:state"

    def test_history_key_format(self):
        """历史 key 格式正确."""
        key = state_service._history_key("test-player-123")
        assert key == "sao:player:test-player-123:chat:history"

    def test_summary_key_format(self):
        """摘要 key 格式正确."""
        key = state_service._summary_key("test-player-123")
        assert key == "sao:player:test-player-123:chat:summary"

    def test_auth_key_format(self):
        """认证 key 格式正确."""
        key = state_service._auth_key("token-abc")
        assert key == "sao:auth:token:token-abc"


class TestLoadPlayerState:
    """Tests for load_player_state function."""

    @pytest.mark.asyncio
    async def test_load_from_redis_cache_hit(self, fake_redis, player_id):
        """从 Redis 缓存加载."""
        # Given: Redis 中有缓存
        state_data = {
            "name": "TestPlayer",
            "level": "5",
            "current_hp": "150",
            "max_hp": "200",
        }
        key = state_service._state_key(player_id)
        await fake_redis.hset(key, mapping=state_data)

        # When: 加载玩家状态
        with patch('gameserver.db.state_service.get_pg') as mock_pg:
            state = await state_service.load_player_state(player_id)

        # Then: 应该从 Redis 返回，不调用 PG
        assert state["name"] == "TestPlayer"
        assert state["level"] == "5"
        mock_pg.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_from_postgres_cache_miss(self, fake_redis, player_id, mock_get_pg):
        """Redis 未命中时从 PG 加载."""
        # Given: Redis 为空，PG 有数据
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, key: {
            "id": "char-123",
            "name": "TestPlayer",
            "level": 5,
            "current_hp": 150,
            "max_hp": 200,
            "experience": 1000,
            "exp_to_next": 200,
            "stat_str": 12,
            "stat_agi": 14,
            "stat_vit": 10,
            "stat_int": 8,
            "stat_dex": 16,
            "stat_luk": 10,
            "col": 500,
            "current_floor": 1,
            "current_area": "起始之城",
            "current_location": "中央广场",
            "stat_points_available": 0,
        }[key]

        mock_get_pg.fetchrow = AsyncMock(return_value=mock_row)

        # When: 加载玩家状态
        state = await state_service.load_player_state(player_id)

        # Then: 应该从 PG 加载并缓存到 Redis
        assert state["name"] == "TestPlayer"
        assert state["level"] == "5"
        assert state["current_hp"] == "150"

    @pytest.mark.asyncio
    async def test_load_player_not_found(self, fake_redis, player_id, mock_get_pg):
        """玩家不存在时返回空字典."""
        # Given: Redis 和 PG 都没有数据
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        # When: 加载玩家状态
        state = await state_service.load_player_state(player_id)

        # Then: 返回空字典
        assert state == {}


class TestSavePlayerState:
    """Tests for save_player_state function."""

    @pytest.mark.asyncio
    async def test_save_to_redis(self, fake_redis, player_id, mock_get_pg):
        """保存状态到 Redis."""
        # Given: 状态变更
        state_changes = {
            "current_hp": "100",
            "level": "6",
        }
        mock_get_pg.execute = AsyncMock(return_value=None)

        # When: 保存状态
        await state_service.save_player_state(player_id, state_changes)

        # Then: Redis 中应该有更新的数据
        key = state_service._state_key(player_id)
        cached = await fake_redis.hgetall(key)
        assert cached["current_hp"] == "100"
        assert cached["level"] == "6"


class TestChatHistory:
    """Tests for chat history operations."""

    @pytest.mark.asyncio
    async def test_push_message(self, fake_redis, player_id, mock_get_pg):
        """保存聊天消息."""
        # Given: 消息和 mock PG
        message = {"role": "user", "content": "Hello"}
        mock_get_pg.execute = AsyncMock()

        # When: 保存消息
        length = await state_service.push_message(
            player_id, message["role"], message["content"]
        )

        # Then: Redis list 应该有消息
        key = state_service._history_key(player_id)
        assert length >= 1
        messages = await fake_redis.lrange(key, 0, -1)
        assert len(messages) >= 1
        
        # 验证消息格式
        import json
        stored = json.loads(messages[0])
        assert stored["role"] == "user"
        assert stored["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_get_recent_messages_from_redis(self, fake_redis, player_id):
        """从 Redis 获取最近消息."""
        # Given: 多条消息（直接写入 Redis）
        import json
        key = state_service._history_key(player_id)
        # 写入顺序：Message 1, Response 1, Message 2
        # lpush 后 Redis 列表：[Message 2, Response 1, Message 1]（最新在头部）
        # lrange 0,-1 返回：[Message 2, Response 1, Message 1]
        # reversed 后：[Message 1, Response 1, Message 2]（ chronological order）
        test_msgs = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
        ]
        for msg in test_msgs:
            await fake_redis.lpush(key, json.dumps(msg))

        # When: 获取最近消息
        recent = await state_service.get_recent_messages(player_id, count=10)

        # Then: 应该返回消息（反转为 chronological order）
        assert len(recent) == 3
        assert recent[0]["content"] == "Message 1"  # 最旧的
        assert recent[2]["content"] == "Message 2"  # 最新的

    @pytest.mark.asyncio
    async def test_get_recent_messages_limit(self, fake_redis, player_id):
        """获取消息时限制数量."""
        # Given: 多条消息
        import json
        key = state_service._history_key(player_id)
        for i in range(10):
            await fake_redis.lpush(key, json.dumps({
                "role": "user",
                "content": f"Message {i}"
            }))

        # When: 获取最近 5 条
        recent = await state_service.get_recent_messages(player_id, count=5)

        # Then: 应该返回最多 5 条
        assert len(recent) == 5


class TestSummary:
    """Tests for conversation summary."""

    @pytest.mark.asyncio
    async def test_save_and_get_summary(self, fake_redis, player_id, mock_get_pg):
        """保存并获取摘要."""
        # Given: 摘要文本和 mock PG
        summary = "玩家在 starting city 击败了 10 只怪物"
        mock_get_pg.execute = AsyncMock()

        # When: 保存摘要
        await state_service.save_summary(player_id, summary)

        # Then: 应该能获取
        key = state_service._summary_key(player_id)
        stored = await fake_redis.get(key)
        assert stored == summary
        
        # 从 Redis 获取
        result = await state_service.get_summary(player_id)
        assert result == summary

    @pytest.mark.asyncio
    async def test_get_summary_not_exists(self, fake_redis, player_id, mock_get_pg):
        """获取不存在的摘要返回 None."""
        # Given: mock PG 返回 None
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        # When: 获取摘要
        result = await state_service.get_summary(player_id)

        # Then: 返回 None
        assert result is None


class TestAuthToken:
    """Tests for auth token operations."""

    @pytest.mark.asyncio
    async def test_store_and_resolve_token(self, fake_redis, player_id):
        """存储并解析 token."""
        # Given: token
        token = "test-token-abc"

        # When: 存储 token
        await state_service.store_auth_token(token, player_id)

        # Then: 应该能解析
        resolved = await state_service.resolve_token(token)
        assert resolved == player_id

    @pytest.mark.asyncio
    async def test_resolve_invalid_token(self, fake_redis):
        """解析无效 token 返回 None."""
        # When: 解析不存在的 token
        result = await state_service.resolve_token("invalid-token")

        # Then: 返回 None
        assert result is None
