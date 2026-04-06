import asyncio
import logging

import grpc

from gameserver.config.settings import Settings
from gameserver.service.chat_service import ChatService

# Import generated gRPC code
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "gen"))
from game.v1 import game_service_pb2
from game.v1 import game_service_pb2_grpc

logger = logging.getLogger(__name__)


class GameServicer(game_service_pb2_grpc.GameServiceServicer):
    """gRPC GameService implementation."""

    def __init__(self, settings: Settings) -> None:
        self._chat_service = ChatService(settings)

    async def Chat(self, request, context):
        """Handle streaming chat requests."""
        message = request.message
        session_id = request.session_id
        model = request.model

        # Input validation
        if not message or not message.strip():
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error="Message cannot be empty"
            )
            return

        if len(message) > 10000:
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error="Message too long (max 10000 chars)"
            )
            return

        logger.info(
            "gRPC Chat: session=%s, model=%s, msg_len=%d",
            session_id, model, len(message),
        )

        try:
            async for chunk in self._chat_service.stream_chat(
                message=message,
                session_id=session_id,
                model=model,
            ):
                yield game_service_pb2.ChatResponse(
                    content=chunk, is_done=False, error=""
                )

            # Final message indicating stream is done
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error=""
            )

        except Exception as e:
            logger.error("Chat error: %s", str(e), exc_info=True)
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error=str(e)
            )
