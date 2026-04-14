"""Tests for redis_client module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestRedisConnection:
    """Tests for Redis connection."""

    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        """成功初始化 Redis 连接."""
        from gameserver.db import redis_client
        
        # Reset client
        redis_client._redis = None
        
        mock_redis = AsyncMock()
        
        with patch('gameserver.db.redis_client.aioredis.from_url', return_value=mock_redis) as mock_from_url:
            await redis_client.init_redis("redis://localhost:6379/0")
            
            # Should call from_url
            assert mock_from_url.called
            assert redis_client._redis == mock_redis

    @pytest.mark.asyncio
    async def test_get_redis_not_initialized(self):
        """未初始化时获取抛出异常."""
        from gameserver.db.redis_client import get_redis
        from gameserver.db import redis_client
        
        # Reset client
        redis_client._redis = None
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Redis not initialized"):
            get_redis()

    @pytest.mark.asyncio
    async def test_get_redis_returns_client(self):
        """初始化后获取 Redis 客户端."""
        from gameserver.db.redis_client import get_redis
        from gameserver.db import redis_client
        
        # Set mock client
        mock_redis = AsyncMock()
        redis_client._redis = mock_redis
        
        # Should return client
        client = get_redis()
        assert client == mock_redis

    @pytest.mark.asyncio
    async def test_close_redis(self):
        """关闭 Redis 连接."""
        from gameserver.db.redis_client import close_redis
        from gameserver.db import redis_client
        
        # Set mock client with aclose (async close)
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        redis_client._redis = mock_redis
        
        # Close
        await close_redis()
        
        # Should close connection with aclose
        mock_redis.aclose.assert_called_once()
        assert redis_client._redis is None
