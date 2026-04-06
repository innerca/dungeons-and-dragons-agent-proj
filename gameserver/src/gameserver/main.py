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

from gameserver.config.settings import Settings
from gameserver.grpc_service.game_servicer import GameServicer

# Load .env from project root
from dotenv import load_dotenv
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def serve() -> None:
    config_path = os.environ.get(
        "GAMESERVER_CONFIG",
        str(Path(__file__).parent.parent.parent / "config" / "config.yaml"),
    )
    settings = Settings.load(config_path)

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
    logger.info("GameServer stopped")


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
