"""Tests for quest_service module."""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gameserver.game import quest_service
from gameserver.game.quest_service import (
    get_active_quests,
    get_quest_status,
    accept_quest,
    update_quest_progress,
    check_quest_triggers,
    _check_prerequisites,
)


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


class TestAcceptQuest:
    """Tests for accept_quest function."""

    @pytest.mark.asyncio
    async def test_accept_quest_success(self, mock_get_pg, player_id):
        """成功接受任务."""
        char_id = str(uuid.uuid4())
        
        # Setup mock character lookup
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        # Setup mock quest row (available status)
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "status": "available",
            "name": "击败哥布林",
            "objectives_json": [
                {"type": "kill", "target": "goblin", "count": 5, "desc": "哥布林"}
            ],
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,  # Character lookup
            mock_quest_row,  # Quest status
        ])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Execute
        result = await accept_quest(player_id, "quest_001")

        # Verify
        assert result["success"] is True
        assert "击败哥布林" in result["message"]
        assert result["quest_name"] == "击败哥布林"

    @pytest.mark.asyncio
    async def test_accept_quest_no_character(self, mock_get_pg, player_id):
        """没有角色时失败."""
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        result = await accept_quest(player_id, "quest_001")

        assert result["success"] is False
        assert "未创建角色" in result["message"]

    @pytest.mark.asyncio
    async def test_accept_quest_not_unlocked(self, mock_get_pg, player_id):
        """任务未解锁时失败."""
        char_id = str(uuid.uuid4())
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            None,  # Quest not found
        ])

        result = await accept_quest(player_id, "quest_001")

        assert result["success"] is False
        assert "未解锁" in result["message"]

    @pytest.mark.asyncio
    async def test_accept_quest_already_active(self, mock_get_pg, player_id):
        """任务已在进行中时失败."""
        char_id = str(uuid.uuid4())
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "status": "active",
            "name": "击败哥布林",
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_quest_row,
        ])

        result = await accept_quest(player_id, "quest_001")

        assert result["success"] is False
        assert "已在进行中" in result["message"]

    @pytest.mark.asyncio
    async def test_accept_quest_already_completed(self, mock_get_pg, player_id):
        """任务已完成时失败."""
        char_id = str(uuid.uuid4())
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "status": "completed",
            "name": "击败哥布林",
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_quest_row,
        ])

        result = await accept_quest(player_id, "quest_001")

        assert result["success"] is False
        assert "已完成" in result["message"]


class TestQuestProgressEdgeCases:
    """Tests for quest progress edge cases."""

    @pytest.mark.asyncio
    async def test_update_quest_progress_complete_objective(self, mock_get_pg, player_id):
        """完成目标时进度正确更新."""
        char_id = str(uuid.uuid4())
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 1,
            "quest_def_id": "quest_001",
            "progress_json": {
                "obj_0": {"current": 2, "required": 3, "completed": False, "type": "kill", "target": "wolf"}
            },
            "name": "击败野狼",
            "objectives_json": [{"type": "kill", "target": "wolf", "count": 3}],
            "rewards_json": {"exp": 100, "col": 50},
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Mock redis to avoid initialization error
        with patch('gameserver.db.redis_client.get_redis') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Execute: Kill 1 wolf (will complete objective)
            messages = await update_quest_progress(
                player_id, "kill", "wolf", 1
            )

            # Verify
            assert len(messages) > 0
            assert any("目标完成" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_update_quest_progress_partial_update(self, mock_get_pg, player_id):
        """部分更新进度."""
        char_id = str(uuid.uuid4())
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 1,
            "quest_def_id": "quest_001",
            "progress_json": {
                "obj_0": {"current": 0, "required": 3, "completed": False, "type": "kill", "target": "wolf"}
            },
            "name": "击败野狼",
            "objectives_json": [{"type": "kill", "target": "wolf", "count": 3}],
            "rewards_json": {},
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Execute: Kill 1 wolf (partial progress)
        messages = await update_quest_progress(
            player_id, "kill", "wolf", 1
        )

        # Verify
        assert len(messages) > 0
        assert any("1/3" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_update_quest_progress_wrong_target(self, mock_get_pg, player_id):
        """击杀错误目标不更新进度."""
        char_id = str(uuid.uuid4())
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 1,
            "quest_def_id": "quest_001",
            "progress_json": {
                "obj_0": {"current": 0, "required": 3, "completed": False, "type": "kill", "target": "wolf"}
            },
            "name": "击败野狼",
            "objectives_json": [{"type": "kill", "target": "wolf", "count": 3}],
            "rewards_json": {},
        }[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Execute: Kill goblin (wrong target)
        messages = await update_quest_progress(
            player_id, "kill", "goblin", 1
        )

        # Verify: No messages for wrong target
        assert messages == []


class TestQuestTriggersEdgeCases:
    """Tests for quest trigger edge cases."""

    @pytest.mark.asyncio
    async def test_check_quest_triggers_auto(self, mock_get_pg, player_id):
        """自动触发任务."""
        mock_quest_def = MagicMock()
        mock_quest_def.__getitem__ = lambda s, key: {
            "id": "quest_001",
            "name": "自动任务",
            "prerequisites_json": {},
            "trigger_json": {"type": "auto"},
        }[key]

        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_def])
        mock_get_pg.fetchrow = AsyncMock(return_value=None)
        mock_get_pg.execute = AsyncMock(return_value=None)

        char_id = str(uuid.uuid4())
        state = {"current_floor": 1, "character_id": char_id}

        triggered = await check_quest_triggers(
            player_id, state, "any", "any"
        )

        assert "自动任务" in triggered

    @pytest.mark.asyncio
    async def test_check_quest_triggers_prerequisites_not_met(self, mock_get_pg, player_id):
        """前置条件不满足时不触发."""
        mock_quest_def = MagicMock()
        mock_quest_def.__getitem__ = lambda s, key: {
            "id": "quest_001",
            "name": "高级任务",
            "prerequisites_json": {"min_level": 10},
            "trigger_json": {"type": "location", "target": "起始之城"},
        }[key]

        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_def])
        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        state = {"current_floor": 1, "level": 5, "character_id": str(uuid.uuid4())}

        triggered = await check_quest_triggers(
            player_id, state, "location", "起始之城"
        )

        assert triggered == []

    @pytest.mark.asyncio
    async def test_check_quest_triggers_already_has_quest(self, mock_get_pg, player_id):
        """已有任务时不重复触发."""
        mock_quest_def = MagicMock()
        mock_quest_def.__getitem__ = lambda s, key: {
            "id": "quest_001",
            "name": "测试任务",
            "prerequisites_json": {},
            "trigger_json": {"type": "location", "target": "起始之城"},
        }[key]

        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_def])
        # Simulate player already has this quest
        mock_get_pg.fetchrow = AsyncMock(return_value={"status": "active"})

        state = {"current_floor": 1, "character_id": str(uuid.uuid4())}

        triggered = await check_quest_triggers(
            player_id, state, "location", "起始之城"
        )

        assert triggered == []


# ====================================================================
# 任务进度更新测试 (覆盖 329-397 行)
# ====================================================================

class TestUpdateQuestProgress:
    """Tests for quest progress update."""

    @pytest.mark.asyncio
    async def test_update_progress_kill_event(self, mock_get_pg, player_id):
        """更新击杀类任务进度."""
        # Given: 进行中的任务，目标是击杀哥布林
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 1,
            "quest_def_id": "quest_kill_goblins",
            "name": "哥布林讨伐",
            "objectives_json": [
                {"type": "kill", "target": "goblin", "count": 5, "desc": "哥布林"}
            ],
            "progress_json": '{"obj_0": {"current": 0, "required": 5, "completed": false}}',
        }[key]
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.uuid4()}[key]
        
        # fetchrow 第一次返回 character，第二次返回 quest progress
        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            {"progress_json": '{"obj_0": {"current": 0, "required": 5, "completed": false}}'}
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock()
        
        # When: 击杀一个哥布林
        messages = await quest_service.update_quest_progress(
            player_id, "kill", "goblin", 1
        )
        
        # Then: 应该返回进度更新消息
        assert len(messages) > 0
        assert "哥布林讨伐" in messages[0]
        assert mock_get_pg.execute.called  # 应该更新数据库

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_update_progress_reach_event(self, mock_redis, mock_get_pg, player_id):
        """更新到达类任务进度."""
        # Given: 进行中的任务，目标是到达某地
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 2,
            "quest_def_id": "quest_explore_city",
            "name": "探索城市",
            "objectives_json": [
                {"type": "reach", "target": "起始之城", "count": 1, "desc": "到达起始之城"}
            ],
            "progress_json": '{"obj_0": {"current": 0, "required": 1, "completed": false}}',
            "rewards_json": '{"exp": 100}',
        }[key]
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.uuid4()}[key]
        
        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            {"progress_json": '{"obj_0": {"current": 0, "required": 1, "completed": false}}'}
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 到达起始之城
        messages = await quest_service.update_quest_progress(
            player_id, "reach", "起始之城", 1
        )
        
        # Then: 应该返回进度消息
        assert len(messages) > 0
        assert "探索城市" in messages[0]

    @pytest.mark.asyncio
    async def test_update_progress_no_matching_quest(self, mock_get_pg, player_id):
        """没有匹配的任务时不更新."""
        # Given: 没有进行中的任务
        mock_get_pg.fetch = AsyncMock(return_value=[])
        
        # When: 更新进度
        messages = await quest_service.update_quest_progress(
            player_id, "kill", "dragon", 1
        )
        
        # Then: 应该返回空消息
        assert messages == []

    @pytest.mark.asyncio
    async def test_update_progress_objective_already_completed(self, mock_get_pg, player_id):
        """已完成的目标不再更新."""
        # Given: 任务目标已完成
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 3,
            "quest_def_id": "quest_completed",
            "name": "已完成的任务",
            "objectives_json": [
                {"type": "kill", "target": "wolf", "count": 3, "desc": "狼"}
            ],
            "progress_json": '{"obj_0": {"current": 3, "required": 3, "completed": true}}',
            "rewards_json": '{}',
        }[key]
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.uuid4()}[key]
        
        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,  # character lookup
            {"progress_json": '{"obj_0": {"current": 3, "required": 3, "completed": true}}'}  # quest progress
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock()
        
        # When: 再次击杀狼
        messages = await quest_service.update_quest_progress(
            player_id, "kill", "wolf", 1
        )
        
        # Then: 不应该有更新消息
        assert messages == []
        assert not mock_get_pg.execute.called  # 不应该更新数据库

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_update_progress_complete_all_objectives(self, mock_redis, mock_get_pg, player_id):
        """完成所有目标时触发任务完成."""
        # Given: 任务只有一个目标，这是最后一次更新
        mock_quest_row = MagicMock()
        mock_quest_row.__getitem__ = lambda s, key: {
            "id": 4,
            "quest_def_id": "quest_final_blow",
            "name": "最后一击",
            "objectives_json": [
                {"type": "kill", "target": "boss", "count": 1, "desc": "Boss"}
            ],
            "progress_json": '{"obj_0": {"current": 0, "required": 1, "completed": false}}',
            "rewards_json": '{"exp": 500, "col": 200}',
        }[key]
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.uuid4()}[key]
        
        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,  # character lookup
            {"progress_json": '{"obj_0": {"current": 0, "required": 1, "completed": false}}'}  # quest progress
        ])
        mock_get_pg.fetch = AsyncMock(return_value=[mock_quest_row])
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 击杀Boss（完成目标）
        messages = await quest_service.update_quest_progress(
            player_id, "kill", "boss", 1
        )
        
        # Then: 应该完成任务并返回奖励消息
        assert len(messages) > 0
        assert "最后一击" in messages[0]
        # 应该包含完成消息和奖励消息
        assert any("完成" in msg for msg in messages)


# ====================================================================
# 任务完成和奖励测试 (覆盖 420-499 行)
# ====================================================================

class TestCompleteQuest:
    """Tests for quest completion and rewards."""

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_complete_quest_with_exp_and_col(self, mock_redis, mock_get_pg, player_id):
        """完成任务获得经验和珂尔."""
        # Given: 任务奖励包含经验和珂尔
        char_id = str(uuid.uuid4())
        
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 完成任务
        message = await quest_service._complete_quest(
            player_id,
            char_id,
            "quest_reward_test",
            "奖励任务",
            {"exp": 1000, "col": 500}
        )
        
        # Then: 应该返回完成消息
        assert "奖励任务" in message
        assert "完成" in message
        assert "1000" in message  # 经验值
        assert "500" in message   # 珂尔
        # 应该调用数据库更新
        assert mock_get_pg.execute.call_count >= 3  # 更新状态 + EXP + Col

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_complete_quest_with_items(self, mock_redis, mock_get_pg, player_id):
        """完成任务获得物品奖励."""
        # Given: 任务奖励包含物品
        char_id = str(uuid.uuid4())
        
        mock_item_def = MagicMock()
        mock_item_def.__getitem__ = lambda s, key: {
            "name": "传说之剑",
            "weapon_durability": 200,
        }[key]
        
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_item_def)
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 完成任务
        message = await quest_service._complete_quest(
            player_id,
            char_id,
            "quest_item_reward",
            "物品奖励任务",
            {"items": ["sword_legendary"]}
        )
        
        # Then: 应该获得物品
        assert "物品奖励任务" in message
        assert "传说之剑" in message
        # 应该插入物品到背包
        assert mock_get_pg.execute.call_count >= 2

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_complete_quest_with_flags(self, mock_redis, mock_get_pg, player_id):
        """完成任务设置世界标志."""
        # Given: 任务奖励包含世界标志
        char_id = str(uuid.uuid4())
        
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 完成任务
        message = await quest_service._complete_quest(
            player_id,
            char_id,
            "quest_flag_test",
            "标志任务",
            {"flags": {"story_chapter_1": "completed", "met_kirito": "true"}}
        )
        
        # Then: 应该设置世界标志
        assert "标志任务" in message
        # 应该插入或更新世界标志
        assert mock_get_pg.execute.called

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_complete_quest_with_relationships(self, mock_redis, mock_get_pg, player_id):
        """完成任务更新 NPC 关系."""
        # Given: 任务奖励包含 NPC 关系变化
        char_id = str(uuid.uuid4())
        
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 完成任务
        message = await quest_service._complete_quest(
            player_id,
            char_id,
            "quest_relationship",
            "关系任务",
            {"relationships": {"npc_asuna": 10, "npc_kirito": 5}}
        )
        
        # Then: 应该更新 NPC 关系
        assert "关系任务" in message
        # 应该更新关系表
        assert mock_get_pg.execute.call_count >= 3  # 状态 + 2个关系

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_complete_quest_with_all_rewards(self, mock_redis, mock_get_pg, player_id):
        """完成任务获得所有类型的奖励."""
        # Given: 任务奖励包含所有类型
        char_id = str(uuid.uuid4())
        
        mock_item_def = MagicMock()
        mock_item_def.__getitem__ = lambda s, key: {
            "name": "稀有药水",
            "weapon_durability": None,
        }[key]
        
        mock_get_pg.fetchrow = AsyncMock(return_value=mock_item_def)
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        rewards = {
            "exp": 2000,
            "col": 1000,
            "items": ["potion_rare"],
            "flags": {"quest_chain_complete": "true"},
            "relationships": {"npc_merchant": 15}
        }
        
        # When: 完成任务
        message = await quest_service._complete_quest(
            player_id,
            char_id,
            "quest_all_rewards",
            "全奖励任务",
            rewards
        )
        
        # Then: 应该包含所有奖励
        assert "全奖励任务" in message
        assert "2000" in message  # EXP
        assert "1000" in message  # Col
        assert "稀有药水" in message  # Item
        # 数据库调用应该很多
        assert mock_get_pg.execute.call_count >= 6

    @pytest.mark.asyncio
    @patch('gameserver.db.redis_client.get_redis')
    async def test_complete_quest_empty_rewards(self, mock_redis, mock_get_pg, player_id):
        """完成任务没有奖励."""
        # Given: 任务没有奖励
        char_id = str(uuid.uuid4())
        
        mock_get_pg.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        
        # When: 完成任务
        message = await quest_service._complete_quest(
            player_id,
            char_id,
            "quest_no_reward",
            "无奖励任务",
            {}
        )
        
        # Then: 仍然应该标记为完成
        assert "无奖励任务" in message
        assert "完成" in message
        # 至少更新状态
        assert mock_get_pg.execute.called
