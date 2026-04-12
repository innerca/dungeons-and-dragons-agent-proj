import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import grpc

# Add gen to path for generated gRPC code
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "gen"))
from game.v1 import game_service_pb2_grpc

from gameserver.config.settings import Settings, init_settings
from gameserver.grpc_service.game_servicer import GameServicer
from gameserver.db.postgres import init_pg, close_pg
from gameserver.db.redis_client import init_redis, close_redis
from gameserver.db.chromadb_client import init_chromadb

# Load .env from project root
from dotenv import load_dotenv
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# Configure logging level from environment
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def serve() -> None:
    config_path = os.environ.get(
        "GAMESERVER_CONFIG",
        str(Path(__file__).parent.parent.parent / "config" / "config.yaml"),
    )
    settings = Settings.load(config_path)
    init_settings(settings)

    # Initialize database connections (require DATABASE_URL env var)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        return
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    try:
        await init_pg(database_url)
        await init_redis(redis_url)
    except Exception as e:
        logger.warning(
            "Database connection failed (running without persistence): %s", e
        )

    # Initialize ChromaDB (non-blocking, RAG is optional)
    try:
        chromadb_path = os.environ.get("CHROMADB_PATH")
        init_chromadb(chromadb_path)
    except Exception as e:
        logger.warning("ChromaDB init failed (RAG disabled): %s", e)

    server = grpc.aio.server()
    game_service_pb2_grpc.add_GameServiceServicer_to_server(
        GameServicer(settings), server
    )

    listen_addr = f"[::]:{settings.server.grpc_port}"
    server.add_insecure_port(listen_addr)

    logger.info("GameServer starting on %s", listen_addr)
    logger.info("Default LLM provider: %s", settings.llm.default_provider)

    await server.start()

    # Graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    logger.info("GameServer ready, waiting for requests...")
    await stop_event.wait()

    logger.info("Shutting down gracefully...")
    await server.stop(grace=5)
    await close_pg()
    await close_redis()
    logger.info("GameServer stopped")


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
