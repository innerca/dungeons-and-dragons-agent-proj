"""Tests for quest_service module."""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from gameserver.game import quest_service


class TestGetActiveQuests:
    """Tests for get_active_quests function."""

    @pytest.mark.asyncio
    async def test_get_active_quests(self, mock_get_pg, player_id):
        """mock DB 返回数据."""
        # Setup mock data
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda s, key: {
            "quest_def_id": "quest_001",
            "status": "active",
            "progress_json": {"obj_0": {"current": 2, "required": 3, "completed": False}},
            "name": "Test Quest",
            "quest_type": "main",
            "objectives_json": [{"type": "kill", "target": "wolf", "count": 3}],
            "description": "Kill 3 wolves",
        }[key]

        mock_get_pg.fetch = AsyncMock(return_value=[mock_record])

        # Execute
        quests = await quest_service.get_active_quests(player_id)

        # Verify
        assert len(quests) == 1
        assert quests[0]["quest_id"] == "quest_001"
        assert quests[0]["status"] == "active"
        assert quests[0]["name"] == "Test Quest"
        assert quests[0]["quest_type"] == "main"

    @pytest.mark.asyncio
    async def test_get_active_quests_empty(self, mock_get_pg, player_id):
        """mock DB 返回空列表."""
        mock_get_pg.fetch = AsyncMock(return_value=[])

        quests = await quest_service.get_active_quests(player_id)

        assert quests == []


class TestCheckQuestTriggers:
    """Tests for check_quest_triggers function."""

    @pytest.mark.asyncio
    async def test_check_quest_triggers_location_match(self, mock_get_pg, player_id):
        """触发条件匹配 - location."""
        # Setup mock quest definition
        mock_quest_def = MagicMock()
        mock_quest_def.__getitem__ = lambda s, key: {
            "id": "quest_001",
            "name": "New Quest",
            "prerequisites_json": {},
            "trigger_json": {"type": "location", "target": "起始之城"},
        }[key]

        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_def])
        mock_get_pg.fetchrow = AsyncMock(return_value=None)  # No existing quest
        mock_get_pg.execute = AsyncMock(return_value=None)

        state = {"current_floor": 1, "character_id": str(uuid.uuid4())}

        # Execute
        triggered = await quest_service.check_quest_triggers(
            player_id, state, "location", "起始之城"
        )

        # Verify
        assert "New Quest" in triggered

    @pytest.mark.asyncio
    async def test_check_quest_triggers_no_match(self, mock_get_pg, player_id):
        """触发条件不匹配."""
        mock_quest_def = MagicMock()
        mock_quest_def.__getitem__ = lambda s, key: {
            "id": "quest_001",
            "name": "New Quest",
            "prerequisites_json": {},
            "trigger_json": {"type": "location", "target": "乌尔巴斯"},
        }[key]

        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_def])

        state = {"current_floor": 1}

        triggered = await quest_service.check_quest_triggers(
            player_id, state, "location", "起始之城"
        )

        assert triggered == []


class TestUpdateQuestProgress:
    """Tests for update_quest_progress function."""

    @pytest.mark.asyncio
    async def test_update_quest_progress(self, mock_get_pg, player_id):
        """进度更新."""
        char_id = str(uuid.uuid4())
        
        # Setup mock character lookup
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        # Setup mock quest row
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 1,
            "quest_def_id": "quest_001",
            "progress_json": {"obj_0": {"current": 1, "required": 3, "completed": False, "type": "kill", "target": "wolf"}},
            "name": "Kill Wolves",
            "objectives_json": [{"type": "kill", "target": "wolf", "count": 3}],
            "rewards_json": {"exp": 100},
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,  # First call for character_id
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Execute
        messages = await quest_service.update_quest_progress(
            player_id, "kill", "wolf", 1
        )

        # Verify
        assert len(messages) > 0
        assert any("任务进度" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_update_quest_progress_no_character(self, mock_get_pg, player_id):
        """没有角色时返回空列表."""
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        messages = await quest_service.update_quest_progress(
            player_id, "kill", "wolf", 1
        )

        assert messages == []


class TestCheckPrerequisites:
    """Tests for _check_prerequisites function."""

    @pytest.mark.asyncio
    async def test_check_prerequisites_no_prereqs(self, mock_get_pg, player_id):
        """前置条件校验 - 无条件返回 True."""
        state = {"level": 5}
        result = await quest_service._check_prerequisites(player_id, state, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_check_prerequisites_level_met(self, mock_get_pg, player_id):
        """前置条件校验 - 等级满足."""
        state = {"level": 5}
        prereqs = {"min_level": 3}
        result = await quest_service._check_prerequisites(player_id, state, prereqs)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_prerequisites_level_not_met(self, mock_get_pg, player_id):
        """前置条件校验 - 等级不足."""
        state = {"level": 2}
        prereqs = {"min_level": 3}
        result = await quest_service._check_prerequisites(player_id, state, prereqs)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_prerequisites_required_quests(self, mock_get_pg, player_id):
        """前置条件校验 - 需要前置任务."""
        # Setup mock for quest status check
        mock_status_row = MagicMock()
        mock_status_row.__getitem__ = lambda s, key: {"status": "completed"}[key]
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_status_row)

        state = {"level": 5}
        prereqs = {"required_quests": ["quest_001"]}
        result = await quest_service._check_prerequisites(player_id, state, prereqs)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_prerequisites_required_quests_not_completed(self, mock_get_pg, player_id):
        """前置条件校验 - 前置任务未完成."""
        mock_status_row = MagicMock()
        mock_status_row.__getitem__ = lambda s, key: {"status": "active"}[key]
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_status_row)

        state = {"level": 5}
        prereqs = {"required_quests": ["quest_001"]}
        result = await quest_service._check_prerequisites(player_id, state, prereqs)
        assert result is False
