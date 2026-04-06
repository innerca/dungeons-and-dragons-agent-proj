"""PostgreSQL connection pool using asyncpg."""

import asyncpg
import logging

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pg(database_url: str) -> asyncpg.Pool:
    """Initialize the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        return _pool
    logger.info("Connecting to PostgreSQL...")
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    logger.info("PostgreSQL pool created (min=2, max=10)")
    return _pool


def get_pg() -> asyncpg.Pool:
    """Get the active PostgreSQL pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized. Call init_pg() first.")
    return _pool


async def close_pg() -> None:
    """Close the PostgreSQL pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")
