"""Tests for npc_relationship_service module."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from gameserver.game import npc_relationship_service
from gameserver.game.npc_relationship_service import (
    get_relationship,
    get_all_relationships,
    update_relationship,
    get_relationship_tier,
)


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


class TestGetAllRelationships:
    """Tests for get_all_relationships function."""

    @pytest.mark.asyncio
    async def test_get_all_relationships_multiple(self, mock_get_pg, player_id):
        """获取多个 NPC 关系."""
        mock_rows = [
            MagicMock(__getitem__=lambda s, key: {
                "npc_id": "npc_001",
                "npc_name": "Asuna",
                "relationship_level": 50,
                "interaction_count": 10,
            }[key]),
            MagicMock(__getitem__=lambda s, key: {
                "npc_id": "npc_002",
                "npc_name": "Klein",
                "relationship_level": 20,
                "interaction_count": 5,
            }[key]),
        ]
        
        mock_get_pg.fetch = AsyncMock(return_value=mock_rows)
        
        rels = await get_all_relationships(player_id)
        
        assert len(rels) == 2
        assert rels[0]["npc_name"] == "Asuna"
        assert rels[0]["level"] == 50
        assert rels[1]["npc_name"] == "Klein"
        assert rels[1]["level"] == 20
        # Should be sorted by level DESC
        assert rels[0]["level"] > rels[1]["level"]

    @pytest.mark.asyncio
    async def test_get_all_relationships_empty(self, mock_get_pg, player_id):
        """没有关系时返回空列表."""
        mock_get_pg.fetch = AsyncMock(return_value=[])
        
        rels = await get_all_relationships(player_id)
        
        assert rels == []

    @pytest.mark.asyncio
    async def test_get_all_relationships_null_name(self, mock_get_pg, player_id):
        """NPC 名称为空时使用 npc_id."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, key: {
            "npc_id": "npc_unknown",
            "npc_name": None,
            "relationship_level": 0,
            "interaction_count": 1,
        }[key]
        
        mock_get_pg.fetch = AsyncMock(return_value=[mock_row])
        
        rels = await get_all_relationships(player_id)
        
        assert len(rels) == 1
        assert rels[0]["npc_name"] == "npc_unknown"


class TestUpdateRelationshipEdgeCases:
    """Tests for update_relationship edge cases."""

    @pytest.mark.asyncio
    async def test_update_relationship_no_character(self, mock_get_pg, player_id):
        """没有角色时返回 0."""
        mock_get_pg.fetchrow = AsyncMock(return_value=None)
        
        new_level = await update_relationship(player_id, "npc_001", 10)
        
        assert new_level == 0

    @pytest.mark.asyncio
    async def test_update_relationship_first_interaction(self, mock_get_pg, player_id):
        """首次交互使用 initial_relationship."""
        char_id = str(uuid.uuid4())
        npc_id = "npc_001"
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_npc_row = MagicMock()
        mock_npc_row.__getitem__ = lambda s, key: {"initial_relationship": 10}[key]
        
        mock_result_row = MagicMock()
        mock_result_row.__getitem__ = lambda s, key: {"relationship_level": 20}[key]
        
        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_npc_row,
            mock_result_row,
        ])
        mock_get_pg.execute = AsyncMock(return_value=None)
        
        new_level = await update_relationship(player_id, npc_id, 10)
        
        # initial (10) + delta (10) = 20
        assert new_level == 20

    @pytest.mark.asyncio
    async def test_update_relationship_with_summary(self, mock_get_pg, player_id):
        """更新关系时携带交互摘要."""
        char_id = str(uuid.uuid4())
        npc_id = "npc_001"
        
        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]
        
        mock_npc_row = MagicMock()
        mock_npc_row.__getitem__ = lambda s, key: {"initial_relationship": 0}[key]
        
        mock_result_row = MagicMock()
        mock_result_row.__getitem__ = lambda s, key: {"relationship_level": 5}[key]
        
        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_npc_row,
            mock_result_row,
        ])
        mock_get_pg.execute = AsyncMock(return_value=None)
        
        new_level = await update_relationship(
            player_id, npc_id, 5,
            interaction_summary="帮助了村民"
        )
        
        assert new_level == 5
        # fetchrow handles the UPDATE ... RETURNING

    @pytest.mark.asyncio
    async def test_update_relationship_query_casts_numeric_params(self, mock_get_pg, player_id):
        """关系值运算对 SQL 参数做显式整数类型约束."""
        char_id = str(uuid.uuid4())
        npc_id = "npc_001"

        mock_char_row = MagicMock()
        mock_char_row.__getitem__ = lambda s, key: {"id": uuid.UUID(char_id)}[key]

        mock_npc_row = MagicMock()
        mock_npc_row.__getitem__ = lambda s, key: {"initial_relationship": 0}[key]

        mock_result_row = MagicMock()
        mock_result_row.__getitem__ = lambda s, key: {"relationship_level": 1}[key]

        mock_get_pg.fetchrow = AsyncMock(side_effect=[
            mock_char_row,
            mock_npc_row,
            mock_result_row,
        ])

        await update_relationship(player_id, npc_id, 1)

        update_call = mock_get_pg.fetchrow.await_args_list[2]
        query = update_call.args[0]

        assert "$3::integer + $4::integer" in query
        assert "relationship_level + $4::integer" in query


class TestRelationshipTierBoundaries:
    """Tests for relationship tier boundaries."""

    def test_tier_boundary_80(self):
        """测试 80 分界点."""
        assert get_relationship_tier(80) == "挚友"
        assert get_relationship_tier(79) == "亲密"

    def test_tier_boundary_50(self):
        """测试 50 分界点."""
        assert get_relationship_tier(50) == "亲密"
        assert get_relationship_tier(49) == "友好"

    def test_tier_boundary_20(self):
        """测试 20 分界点."""
        assert get_relationship_tier(20) == "友好"
        assert get_relationship_tier(19) == "中立"

    def test_tier_boundary_0(self):
        """测试 0 分界点."""
        assert get_relationship_tier(0) == "中立"
        assert get_relationship_tier(-1) == "冷淡"

    def test_tier_boundary_negative_30(self):
        """测试 -30 分界点."""
        assert get_relationship_tier(-30) == "冷淡"
        assert get_relationship_tier(-31) == "敌对"

    def test_tier_boundary_negative_60(self):
        """测试 -60 分界点."""
        assert get_relationship_tier(-60) == "敌对"
        assert get_relationship_tier(-61) == "仇恨"

    def test_tier_extreme_values(self):
        """测试极端值."""
        assert get_relationship_tier(1000) == "挚友"
        assert get_relationship_tier(-1000) == "仇恨"
