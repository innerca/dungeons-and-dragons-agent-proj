"""Pytest fixtures for GameServer tests."""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio

from gameserver.config.settings import Settings, init_settings
from gameserver.db import redis_client


# ------------------------------------------------------------------
# Settings fixture
# ------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_settings():
    """Initialize settings for all tests."""
    settings = Settings()
    init_settings(settings)
    return settings


# ------------------------------------------------------------------
# Redis fixtures (using fakeredis)
# ------------------------------------------------------------------

@pytest_asyncio.fixture
async def fake_redis():
    """Provide a fake Redis client for testing."""
    fake_redis_instance = fakeredis.aioredis.FakeRedis(decode_responses=True)
    # Patch the global _redis variable
    original_redis = redis_client._redis
    redis_client._redis = fake_redis_instance
    
    yield fake_redis_instance
    
    # Cleanup
    await fake_redis_instance.flushall()
    redis_client._redis = original_redis


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client with pre-configured async methods."""
    mock = MagicMock()
    mock.hset = AsyncMock(return_value=1)
    mock.hgetall = AsyncMock(return_value={})
    mock.delete = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.llen = AsyncMock(return_value=0)
    mock.lrange = AsyncMock(return_value=[])
    mock.ltrim = AsyncMock(return_value=True)
    mock.lpush = AsyncMock(return_value=1)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    
    # Patch the global _redis variable
    original_redis = redis_client._redis
    redis_client._redis = mock
    
    yield mock
    
    # Restore
    redis_client._redis = original_redis


# ------------------------------------------------------------------
# PostgreSQL fixtures (using AsyncMock)
# ------------------------------------------------------------------

@pytest.fixture
def mock_pg_pool():
    """Provide a mock PostgreSQL pool with pre-configured async methods."""
    mock_pool = MagicMock()
    
    # Mock fetchrow to return None by default
    mock_pool.fetchrow = AsyncMock(return_value=None)
    
    # Mock fetch to return empty list by default
    mock_pool.fetch = AsyncMock(return_value=[])
    
    # Mock execute to return None
    mock_pool.execute = AsyncMock(return_value=None)
    
    return mock_pool


@pytest.fixture
def mock_get_pg(mock_pg_pool, monkeypatch):
    """Mock the get_pg function to return the mock pool."""
    from gameserver.db import postgres
    
    # Initialize _pool to avoid RuntimeError
    monkeypatch.setattr(postgres, "_pool", mock_pg_pool)
    
    def mock_get_pg_func():
        return mock_pg_pool
    
    # Temporarily replace get_pg
    monkeypatch.setattr(postgres, "get_pg", mock_get_pg_func)
    
    yield mock_pg_pool


# ------------------------------------------------------------------
# Common test data fixtures
# ------------------------------------------------------------------

@pytest.fixture
def player_id():
    """Generate a test player ID."""
    return str(uuid.uuid4())


@pytest.fixture
def character_id():
    """Generate a test character ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_player_state(character_id):
    """Provide a sample player state dictionary."""
    return {
        "character_id": character_id,
        "name": "TestPlayer",
        "level": 5,
        "current_hp": 150,
        "max_hp": 200,
        "experience": 500,
        "exp_to_next": 1000,
        "col": 1000,
        "stat_str": 12,
        "stat_agi": 14,
        "stat_vit": 10,
        "stat_int": 8,
        "stat_dex": 16,
        "stat_luk": 10,
        "current_floor": 1,
        "current_area": "起始之城",
        "current_location": "中央广场",
    }


@pytest.fixture
def sample_monster_def():
    """Provide a sample monster definition."""
    return {
        "id": "test_wolf_001",
        "name": "测试野狼",
        "monster_type": "normal",
        "hp": 80,
        "atk": 15,
        "defense": 5,
        "ac": 12,
        "abilities_json": [{"name": "撕咬", "damage": 1.2}],
    }


@pytest.fixture
def sample_quest_def():
    """Provide a sample quest definition."""
    return {
        "id": "quest_001",
        "name": "测试任务",
        "quest_type": "main",
        "description": "这是一个测试任务",
        "objectives_json": [
            {"type": "kill", "target": "test_wolf_001", "count": 3, "desc": "击败3只野狼"},
            {"type": "reach", "target": "起始之城", "count": 1, "desc": "到达起始之城"},
        ],
        "prerequisites_json": {"min_level": 3},
        "trigger_json": {"type": "location", "target": "起始之城"},
        "rewards_json": {"exp": 100, "col": 50, "items": []},
    }


@pytest.fixture
def sample_npc_def():
    """Provide a sample NPC definition."""
    return {
        "id": "npc_001",
        "name": "测试NPC",
        "name_en": "TestNPC",
        "npc_type": "merchant",
        "initial_relationship": 10,
        "appearance": "一个看起来很友善的商人",
        "personality": "热情、健谈",
        "dialog_style": "友好",
    }


# ------------------------------------------------------------------
# Async event loop configuration
# ------------------------------------------------------------------

def pytest_configure(config):
    """Configure pytest-asyncio."""
    config.option.asyncio_mode = "auto"
