"""Tests for postgres module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestPostgresConnection:
    """Tests for PostgreSQL connection."""

    @pytest.mark.asyncio
    async def test_init_pg_success(self):
        """成功初始化连接池."""
        from gameserver.db.postgres import init_pg
        import gameserver.db.postgres as pg_module
        
        # Reset pool
        pg_module._pool = None
        
        # Create a proper mock pool that can be awaited
        mock_pool = MagicMock()
        mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
        mock_pool.__aexit__ = AsyncMock(return_value=False)
        
        async def mock_create_pool(*args, **kwargs):
            return mock_pool
        
        with patch('gameserver.db.postgres.asyncpg.create_pool', side_effect=mock_create_pool) as mock_create:
            await init_pg("postgresql://test:test@localhost/test")
            
            # Should call create_pool
            assert mock_create.called
            assert pg_module._pool == mock_pool

    @pytest.mark.asyncio
    async def test_get_pg_not_initialized(self):
        """未初始化时获取抛出异常."""
        from gameserver.db.postgres import get_pg
        import gameserver.db.postgres as pg_module
        
        # Reset pool
        pg_module._pool = None
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="PostgreSQL pool not initialized"):
            get_pg()

    @pytest.mark.asyncio
    async def test_get_pg_returns_pool(self):
        """初始化后获取连接池."""
        from gameserver.db.postgres import get_pg
        import gameserver.db.postgres as pg_module
        
        # Set mock pool
        mock_pool = AsyncMock()
        pg_module._pool = mock_pool
        
        # Should return pool
        pool = get_pg()
        assert pool == mock_pool

    @pytest.mark.asyncio
    async def test_close_pg(self):
        """关闭连接池."""
        from gameserver.db.postgres import close_pg
        import gameserver.db.postgres as pg_module
        
        # Set mock pool with close (not aclose)
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        pg_module._pool = mock_pool
        
        # Close
        await close_pg()
        
        # Should close pool with close()
        mock_pool.close.assert_called_once()
        assert pg_module._pool is None
