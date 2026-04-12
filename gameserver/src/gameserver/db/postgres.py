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
        logger.debug("PostgreSQL pool already initialized")
        return _pool
    db_cfg = get_settings().database
    logger.info("Connecting to PostgreSQL (pool min=%d, max=%d)...", db_cfg.pg_min_size, db_cfg.pg_max_size)
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=db_cfg.pg_min_size,
        max_size=db_cfg.pg_max_size,
        command_timeout=db_cfg.pg_command_timeout,
    )
    logger.info("PostgreSQL pool created successfully (min=%d, max=%d, timeout=%d)", db_cfg.pg_min_size, db_cfg.pg_max_size, db_cfg.pg_command_timeout)
    return _pool


def get_pg() -> asyncpg.Pool:
    """Get the active PostgreSQL pool. Raises if not initialized."""
    if _pool is None:
        logger.error("PostgreSQL pool not initialized")
        raise RuntimeError("PostgreSQL pool not initialized. Call init_pg() first.")
    # Log pool status at debug level
    if _pool is not None:
        logger.debug(
            "PostgreSQL pool status: size=%d, min=%d, max=%d",
            _pool.get_size(), _pool.get_min_size(), _pool.get_max_size()
        )
    return _pool


async def close_pg() -> None:
    """Close the PostgreSQL pool."""
    global _pool
    if _pool is not None:
        logger.debug("Closing PostgreSQL pool...")
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")
