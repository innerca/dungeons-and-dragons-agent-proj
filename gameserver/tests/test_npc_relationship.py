"""Tests for npc_relationship_service module."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from gameserver.game import npc_relationship_service


class TestGetRelationshipTier:
    """Tests for get_relationship_tier function."""

    def test_get_relationship_tier_mapping_80(self):
        """7 级映射正确 - 挚友 (>=80)."""
        tier = npc_relationship_service.get_relationship_tier(80)
        assert tier == "挚友"

    def test_get_relationship_tier_mapping_50(self):
        """7 级映射正确 - 亲密 (>=50)."""
        tier = npc_relationship_service.get_relationship_tier(50)
        assert tier == "亲密"

    def test_get_relationship_tier_mapping_20(self):
        """7 级映射正确 - 友好 (>=20)."""
        tier = npc_relationship_service.get_relationship_tier(20)
        assert tier == "友好"

    def test_get_relationship_tier_mapping_0(self):
        """7 级映射正确 - 中立 (>=0)."""
        tier = npc_relationship_service.get_relationship_tier(0)
        assert tier == "中立"

    def test_get_relationship_tier_mapping_negative_30(self):
        """7 级映射正确 - 冷淡 (>=-30)."""
        tier = npc_relationship_service.get_relationship_tier(-30)
        assert tier == "冷淡"

    def test_get_relationship_tier_mapping_negative_60(self):
        """7 级映射正确 - 敌对 (>=-60)."""
        tier = npc_relationship_service.get_relationship_tier(-60)
        assert tier == "敌对"

    def test_get_relationship_tier_mapping_negative_100(self):
        """7 级映射正确 - 仇恨 (<=-100)."""
        tier = npc_relationship_service.get_relationship_tier(-100)
        assert tier == "仇恨"

    def test_get_relationship_tier_mapping_100(self):
        """7 级映射正确 - 最大值 100."""
        tier = npc_relationship_service.get_relationship_tier(100)
        assert tier == "挚友"


class TestUpdateRelationship:
    """Tests for update_relationship function."""

    @pytest.mark.asyncio
    async def test_update_relationship_clamp_max(self, mock_get_pg, player_id):
        """关系值不超过 100 边界."""
        char_id = str(uuid.uuid4())
        npc_id = "npc_001"

        # Setup mocks
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]

        mock_npc_row = MagicMock()
        mock_npc_row.__getitem__ = lambda s, key: {"initial_relationship": 90}[key]

        mock_result_row = MagicMock()
        mock_result_row.__getitem__ = lambda s, key: {"relationship_level": 100}[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_npc_row,
            mock_result_row,
        ])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Try to add 20 to a relationship at 90 (should clamp to 100)
        new_level = await npc_relationship_service.update_relationship(
            player_id, npc_id, 20
        )

        assert new_level == 100

    @pytest.mark.asyncio
    async def test_update_relationship_clamp_min(self, mock_get_pg, player_id):
        """关系值不超过 -100 边界."""
        char_id = str(uuid.uuid4())
        npc_id = "npc_001"

        # Setup mocks
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]

        mock_npc_row = MagicMock()
        mock_npc_row.__getitem__ = lambda s, key: {"initial_relationship": -90}[key]

        mock_result_row = MagicMock()
        mock_result_row.__getitem__ = lambda s, key: {"relationship_level": -100}[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_npc_row,
            mock_result_row,
        ])
        mock_get_pg.execute = AsyncMock(return_value=None)

        # Try to subtract 20 from a relationship at -90 (should clamp to -100)
        new_level = await npc_relationship_service.update_relationship(
            player_id, npc_id, -20
        )

        assert new_level == -100


class TestGetRelationship:
    """Tests for get_relationship function."""

    @pytest.mark.asyncio
    async def test_get_relationship_existing(self, mock_get_pg, player_id):
        """mock DB 返回已有关系."""
        npc_id = "npc_001"

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, key: {
            "relationship_level": 25,
            "interaction_count": 5,
            "last_interaction_summary": "Had a nice chat",
        }[key]

        mock_get_pg.fetchrow = AsyncMock(return_value=mock_row)

        rel = await npc_relationship_service.get_relationship(player_id, npc_id)

        assert rel["level"] == 25
        assert rel["interaction_count"] == 5
        assert rel["last_summary"] == "Had a nice chat"

    @pytest.mark.asyncio
    async def test_get_relationship_fallback(self, mock_get_pg, player_id):
        """mock DB 返回初始关系."""
        npc_id = "npc_001"

        # First call returns None (no existing relationship)
        # Second call returns npc definition
        mock_npc_row = MagicMock()
        mock_npc_row.__getitem__ = lambda s, key: {"initial_relationship": 10}[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            None,  # No existing relationship
            mock_npc_row,  # NPC definition with initial relationship
        ])

        rel = await npc_relationship_service.get_relationship(player_id, npc_id)

        assert rel["level"] == 10
        assert rel["interaction_count"] == 0
        assert rel["last_summary"] is None

    @pytest.mark.asyncio
    async def test_get_relationship_no_character(self, mock_get_pg, player_id):
        """没有角色时返回初始关系 0."""
        npc_id = "npc_001"

        mock_get_pg.fetchrow = AsyncMock(return_value=None)

        rel = await npc_relationship_service.get_relationship(player_id, npc_id)

        assert rel["level"] == 0
        assert rel["interaction_count"] == 0
