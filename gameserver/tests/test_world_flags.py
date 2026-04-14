"""Tests for world_flags_service module."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from gameserver.game import world_flags_service


class TestSetAndGetFlag:
    """Tests for set_flag and get_flag functions."""

    @pytest.mark.asyncio
    async def test_set_and_get_flag_writes_and_reads_consistently(self, mock_get_pg, player_id):
        """写入后读取一致."""
        char_id = str(uuid.uuid4())
        flag_key = "test_flag"
        flag_value = "test_value"

        # Given: 角色存在
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_char_row)
        mock_get_pg.execute = AsyncMock(return_value=None)

        # When: 设置 flag
        await world_flags_service.set_flag(player_id, flag_key, flag_value)

        # Then: 验证 execute 被调用（写入数据库）
        mock_get_pg.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_flag_returns_value_when_exists(self, mock_get_pg, player_id):
        """flag 存在时返回对应值."""
        flag_key = "existing_flag"
        expected_value = "flag_value"

        # Given: flag 存在于数据库
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, key: {"flag_value": expected_value}[key]
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_row)

        # When: 获取 flag
        value = await world_flags_service.get_flag(player_id, flag_key)

        # Then: 返回正确的值
        assert value == expected_value

    @pytest.mark.asyncio
    async def test_get_flag_returns_none_when_not_exists(self, mock_get_pg, player_id):
        """flag 不存在时返回 None."""
        flag_key = "nonexistent_flag"

        # Given: flag 不存在
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        # When: 获取 flag
        value = await world_flags_service.get_flag(player_id, flag_key)

        # Then: 返回 None
        assert value is None


class TestCheckFlagMatch:
    """Tests for check_flag function."""

    @pytest.mark.asyncio
    async def test_check_flag_match_returns_true_when_matches(self, mock_get_pg, player_id):
        """匹配时返回 True."""
        flag_key = "quest_completed"
        expected_value = "true"

        # Given: flag 值与预期匹配
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, key: {"flag_value": "true"}[key]
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_row)

        # When: 检查 flag 是否匹配
        result = await world_flags_service.check_flag(player_id, flag_key, expected_value)

        # Then: 返回 True
        assert result is True

    @pytest.mark.asyncio
    async def test_check_flag_match_returns_false_when_not_matches(self, mock_get_pg, player_id):
        """不匹配时返回 False."""
        flag_key = "quest_completed"
        expected_value = "true"

        # Given: flag 值与预期不匹配
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, key: {"flag_value": "false"}[key]
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_row)

        # When: 检查 flag 是否匹配
        result = await world_flags_service.check_flag(player_id, flag_key, expected_value)

        # Then: 返回 False
        assert result is False

    @pytest.mark.asyncio
    async def test_check_flag_match_returns_false_when_not_exists(self, mock_get_pg, player_id):
        """flag 不存在时返回 False."""
        flag_key = "quest_completed"
        expected_value = "true"

        # Given: flag 不存在
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        # When: 检查 flag 是否匹配
        result = await world_flags_service.check_flag(player_id, flag_key, expected_value)

        # Then: 返回 False
        assert result is False


class TestGetAllFlags:
    """Tests for get_all_flags function."""

    @pytest.mark.asyncio
    async def test_get_all_flags_returns_dict_of_flags(self, mock_get_pg, player_id):
        """批量获取所有 flags."""
        # Given: 数据库中有多个 flags
        mock_rows = [
            MagicMock(__getitem__=lambda s, key, i=i: {"flag_key": f"flag_{i}", "flag_value": f"value_{i}"}[key])
            for i in range(3)
        ]
        # Fix the lambda to capture the correct index
        for i, mock_row in enumerate(mock_rows):
            mock_row._index = i
            mock_row.__getitem__ = lambda s, key, idx=i: {"flag_key": f"flag_{idx}", "flag_value": f"value_{idx}"}[key]

        mock_get_pg.fetch = AsyncMock(return_value=mock_rows)

        # When: 获取所有 flags
        flags = await world_flags_service.get_all_flags(player_id)

        # Then: 返回包含所有 flags 的字典
        assert isinstance(flags, dict)
        assert len(flags) == 3
        assert flags["flag_0"] == "value_0"
        assert flags["flag_1"] == "value_1"
        assert flags["flag_2"] == "value_2"

    @pytest.mark.asyncio
    async def test_get_all_flags_returns_empty_dict_when_none(self, mock_get_pg, player_id):
        """没有 flags 时返回空字典."""
        # Given: 数据库中没有 flags
        mock_get_pg.fetch = AsyncMock(return_value=[])

        # When: 获取所有 flags
        flags = await world_flags_service.get_all_flags(player_id)

        # Then: 返回空字典
        assert flags == {}
