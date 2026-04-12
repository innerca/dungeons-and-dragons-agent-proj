"""gRPC GameService implementation with auth, character, and DND game RPCs."""

import logging

import grpc

from gameserver.config.settings import Settings
from gameserver.service.chat_service import ChatService
from gameserver.db import player_repo, state_service

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
        """Handle streaming DND game chat requests."""
        player_id = request.player_id
        message = request.message
        model = request.model

        # Extract trace_id from gRPC metadata
        metadata = dict(context.invocation_metadata())
        trace_id = metadata.get("x-trace-id", "")
        if not trace_id:
            # Generate a short trace_id if not provided
            import uuid
            trace_id = str(uuid.uuid4())[:8]

        if not player_id:
            logger.error("trace=%s step=chat_validation error=missing_player_id", trace_id)
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error="player_id is required"
            )
            return

        if not message or not message.strip():
            logger.error("trace=%s step=chat_validation error=empty_message", trace_id)
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error="Message cannot be empty"
            )
            return

        if len(message) > 10000:
            logger.error("trace=%s step=chat_validation error=message_too_long len=%d", trace_id, len(message))
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error="Message too long (max 10000 chars)"
            )
            return

        logger.info(
            "trace=%s step=chat_request player=%s model=%s msg_len=%d",
            trace_id, player_id, model, len(message),
        )

        try:
            async for result in self._chat_service.stream_chat(
                player_id=player_id,
                message=message,
                model=model,
                trace_id=trace_id,
            ):
                actions = []
                for a in result.get("actions", []):
                    actions.append(game_service_pb2.GameAction(
                        action_type=a.action_type,
                        description=a.description,
                        params={k: str(v) for k, v in a.params.items()},
                        success=a.success,
                        result_summary=a.result_summary,
                    ))

                state_delta = None
                sc = result.get("state_changes", {})
                if sc:
                    state_delta = game_service_pb2.PlayerStateDelta(
                        hp_change=int(sc.get("hp_change", 0)),
                        xp_change=int(sc.get("xp_change", 0)),
                        col_change=int(sc.get("col_change", 0)),
                        new_location=sc.get("new_location", ""),
                    )

                yield game_service_pb2.ChatResponse(
                    content=result.get("content", ""),
                    is_done=result.get("is_done", False),
                    error=result.get("error", ""),
                    actions=actions,
                    state_delta=state_delta,
                )

        except Exception as e:
            logger.error("trace=%s step=chat_error error=%s", trace_id, str(e), exc_info=True)
            yield game_service_pb2.ChatResponse(
                content="", is_done=True, error=str(e)
            )

    async def CreatePlayer(self, request, context):
        """Register a new player."""
        try:
            player_id, token = await player_repo.create_player(
                username=request.username,
                display_name=request.display_name,
                password=request.password,
            )
            # Store token in Redis
            await state_service.store_auth_token(token, player_id)
            logger.info("Player created: %s (%s)", request.username, player_id)
            return game_service_pb2.CreatePlayerResponse(
                player_id=player_id, token=token,
            )
        except ValueError as e:
            return game_service_pb2.CreatePlayerResponse(error=str(e))
        except Exception as e:
            logger.error("CreatePlayer error: %s", e, exc_info=True)
            return game_service_pb2.CreatePlayerResponse(error="Internal error")

    async def AuthenticatePlayer(self, request, context):
        """Authenticate a player and return a token."""
        try:
            player_id, token = await player_repo.authenticate_player(
                username=request.username,
                password=request.password,
            )
            await state_service.store_auth_token(token, player_id)
            logger.info("Player authenticated: %s", request.username)
            return game_service_pb2.AuthResponse(
                player_id=player_id, token=token,
            )
        except ValueError as e:
            return game_service_pb2.AuthResponse(error=str(e))
        except Exception as e:
            logger.error("AuthenticatePlayer error: %s", e, exc_info=True)
            return game_service_pb2.AuthResponse(error="Internal error")

    async def CreateCharacter(self, request, context):
        """Create a character for an authenticated player."""
        try:
            char_id = await player_repo.create_character(
                player_id=request.player_id,
                name=request.name,
                str_=request.stat_str,
                agi=request.stat_agi,
                vit=request.stat_vit,
                int_=request.stat_int,
                dex=request.stat_dex,
                luk=request.stat_luk,
            )
            logger.info("Character created: %s for player %s", request.name, request.player_id)
            return game_service_pb2.CreateCharacterResponse(character_id=char_id)
        except ValueError as e:
            return game_service_pb2.CreateCharacterResponse(error=str(e))
        except Exception as e:
            logger.error("CreateCharacter error: %s", e, exc_info=True)
            return game_service_pb2.CreateCharacterResponse(error="Internal error")

    async def GetPlayerState(self, request, context):
        """Get the current player state."""
        try:
            state = await state_service.load_player_state(request.player_id)
            if not state:
                return game_service_pb2.PlayerStateResponse(error="Character not found")

            return game_service_pb2.PlayerStateResponse(
                character_name=state.get("name", ""),
                level=int(state.get("level", 1)),
                current_hp=int(state.get("current_hp", 0)),
                max_hp=int(state.get("max_hp", 0)),
                experience=int(state.get("experience", 0)),
                exp_to_next=int(state.get("exp_to_next", 100)),
                stat_str=int(state.get("stat_str", 10)),
                stat_agi=int(state.get("stat_agi", 10)),
                stat_vit=int(state.get("stat_vit", 10)),
                stat_int=int(state.get("stat_int", 10)),
                stat_dex=int(state.get("stat_dex", 10)),
                stat_luk=int(state.get("stat_luk", 10)),
                col=int(state.get("col", 0)),
                current_floor=int(state.get("current_floor", 1)),
                current_area=state.get("current_area", ""),
                current_location=state.get("current_location", ""),
            )
        except Exception as e:
            logger.error("GetPlayerState error: %s", e, exc_info=True)
            return game_service_pb2.PlayerStateResponse(error="Internal error")
