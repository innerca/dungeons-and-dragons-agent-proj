"""Redis connection using redis-py async client."""

import redis.asyncio as aioredis
import logging

from gameserver.config.settings import get_settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def init_redis(redis_url: str) -> aioredis.Redis:
    """Initialize the Redis async client."""
    global _redis
    if _redis is not None:
        return _redis
    redis_cfg = get_settings().redis
    logger.info("Connecting to Redis...")
    _redis = aioredis.from_url(
        redis_url,
        decode_responses=True,
        max_connections=redis_cfg.max_connections,
    )
    await _redis.ping()
    logger.info("Redis connected")
    return _redis


def get_redis() -> aioredis.Redis:
    """Get the active Redis client. Raises if not initialized."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")
