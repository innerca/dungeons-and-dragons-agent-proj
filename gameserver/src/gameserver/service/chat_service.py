"""DND Game Engine - Core chat service with ReAct tool calling.

Replaces the simple chat passthrough with a full game loop:
1. Load player state from Redis/PG
2. Build 3-layer memory context
3. ReAct loop (max 5 tool call rounds)
4. Stream narrative response
5. Persist state changes
"""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from gameserver.config.settings import Settings
from gameserver.llm.base import ChatMessage, LLMProvider
from gameserver.llm.factory import LLMProviderFactory
from gameserver.db import state_service
from gameserver.game.context_builder import build_context, maybe_compress_history
from gameserver.game.tools import GAME_TOOLS
from gameserver.game.action_executor import ActionExecutor, ActionResult

logger = logging.getLogger(__name__)

MAX_REACT_ROUNDS = 5


@dataclass
class GameActionProto:
    """Serializable game action for gRPC response."""
    action_type: str
    description: str
    params: dict
    success: bool
    result_summary: str


class ChatService:
    """DND Game Engine with ReAct tool calling."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, LLMProvider] = {}
        self._executor = ActionExecutor()

    def _get_provider(self, provider_name: str | None = None) -> LLMProvider:
        name = provider_name or self._settings.llm.default_provider
        if name not in self._providers:
            config = self._settings.llm.providers.get(name)
            if config is None:
                raise ValueError(
                    f"Provider '{name}' not found. "
                    f"Available: {list(self._settings.llm.providers.keys())}"
                )
            self._providers[name] = LLMProviderFactory.create(config)
            logger.info("Created LLM provider: %s (model=%s)", name, config.model)
        return self._providers[name]

    async def stream_chat(
        self,
        player_id: str,
        message: str,
        model: str = "",
    ) -> AsyncIterator[dict]:
        """Process a game message through the ReAct engine.

        Yields dicts with keys: content, is_done, error, actions, state_changes
        """
        provider_name = model if model in self._settings.llm.providers else None
        provider = self._get_provider(provider_name)

        # Save user message
        await state_service.push_message(player_id, "user", message)

        # Build context (3-layer memory)
        ctx = await build_context(player_id, message, GAME_TOOLS)

        logger.info(
            "Game request: player=%s, provider=%s, msg=%s",
            player_id,
            provider_name or self._settings.llm.default_provider,
            message[:100],
        )

        # ReAct loop
        all_actions: list[GameActionProto] = []
        state = await state_service.load_player_state(player_id)

        for round_idx in range(MAX_REACT_ROUNDS):
            # Call LLM with tools
            try:
                response = await provider.chat_with_tools(
                    messages=[ChatMessage(role=m["role"], content=m["content"]) for m in ctx.messages],
                    tools=ctx.tools,
                )
            except AttributeError:
                # Provider doesn't support tool calling, fall back to streaming
                break
            except Exception as e:
                logger.error("LLM tool call error (round %d): %s", round_idx, e)
                break

            if not response or not hasattr(response, "tool_calls") or not response.tool_calls:
                break

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    tool_args = {}

                logger.info("Tool call: %s(%s)", tool_name, tool_args)

                result = await self._executor.execute(player_id, state, tool_name, tool_args)

                # Record action
                all_actions.append(GameActionProto(
                    action_type=result.action_type,
                    description=result.description,
                    params=tool_args,
                    success=result.success,
                    result_summary=result.description,
                ))

                # Update state if changed
                if result.state_changes:
                    state.update({k: str(v) for k, v in result.state_changes.items()})

                # Add tool result to context
                ctx.messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args, ensure_ascii=False),
                        },
                    }],
                })
                ctx.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.to_tool_result(),
                })

        # Stream final narrative
        narrative_parts = []
        messages = [ChatMessage(role=m["role"], content=m.get("content") or "") for m in ctx.messages]

        try:
            async for chunk in provider.stream_chat(messages):
                narrative_parts.append(chunk)
                yield {
                    "content": chunk,
                    "is_done": False,
                    "actions": [],
                    "state_changes": {},
                }
        except Exception as e:
            logger.error("Streaming error: %s", e, exc_info=True)
            yield {"content": "", "is_done": True, "error": str(e), "actions": [], "state_changes": {}}
            return

        # Save assistant message
        full_narrative = "".join(narrative_parts)
        if full_narrative:
            await state_service.push_message(player_id, "assistant", full_narrative)

        # Compress history if needed
        try:
            await maybe_compress_history(player_id, provider)
        except Exception as e:
            logger.warning("History compression failed: %s", e)

        # Final done message with all actions
        yield {
            "content": "",
            "is_done": True,
            "actions": all_actions,
            "state_changes": {},
        }
