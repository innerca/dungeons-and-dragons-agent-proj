"""PostgreSQL connection pool using asyncpg."""

import asyncpg
import logging

from gameserver.config.settings import get_settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pg(database_url: str) -> asyncpg.Pool:
    """Initialize the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        return _pool
    db_cfg = get_settings().database
    logger.info("Connecting to PostgreSQL...")
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=db_cfg.pg_min_size,
        max_size=db_cfg.pg_max_size,
        command_timeout=db_cfg.pg_command_timeout,
    )
    logger.info("PostgreSQL pool created (min=%d, max=%d)", db_cfg.pg_min_size, db_cfg.pg_max_size)
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
