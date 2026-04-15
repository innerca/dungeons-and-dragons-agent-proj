"""DND Game Engine - Core chat service with ReAct tool calling.

Replaces the simple chat passthrough with a full game loop:
1. Load player state from Redis/PG
2. Build 3-layer memory context
3. ReAct loop (max 5 tool call rounds)
4. Stream narrative response
5. Persist state changes
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

import time

from gameserver.config.settings import Settings
from gameserver.llm.base import ChatMessage, LLMProvider
from gameserver.llm.factory import LLMProviderFactory
from gameserver.llm.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from gameserver.db import state_service
from gameserver.db.chromadb_client import query_combined, COLLECTION_NOVELS
from gameserver.game.context_builder import build_context, maybe_compress_history
from gameserver.game.tools import GAME_TOOLS
from gameserver.game.action_executor import ActionExecutor, ActionResult
from gameserver.game.scene_classifier import classify_scene, prune_tools, get_rag_entity_type
from gameserver.service.request_metrics import RequestMetrics

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
    
    def _get_fallback_provider(self, current_provider: str | None = None) -> LLMProvider | None:
        """Get a fallback provider when the primary fails."""
        # Try to find any provider that's not the current one
        for name, config in self._settings.llm.providers.items():
            if name != current_provider:
                if name not in self._providers:
                    self._providers[name] = LLMProviderFactory.create(config)
                return self._providers[name]
        return None

    async def stream_chat(
        self,
        player_id: str,
        message: str,
        model: str = "",
        trace_id: str = "no-trace",
    ) -> AsyncIterator[dict]:
        """Process a game message through the ReAct engine.

        Yields dicts with keys: content, is_done, error, actions, state_changes
        """
        # Initialize request metrics
        metrics = RequestMetrics(trace_id=trace_id)
        
        provider_name = model if model in self._settings.llm.providers else None
        provider = self._get_provider(provider_name)

        # Check if API key is configured
        if not provider._config.api_key:
            logger.warning(
                "trace=%s step=api_key_check status=empty provider=%s",
                trace_id,
                provider_name or self._settings.llm.default_provider,
            )
            yield {
                "content": "",
                "is_done": True,
                "error": (
                    "⚠️ LLM API Key 未配置！\n\n"
                    "请在 .env 文件中配置 API Key 以启用 AI 功能：\n"
                    "  1. 编辑项目根目录的 .env 文件\n"
                    "  2. 填入你的 DEEPSEEK_API_KEY=sk-xxx\n"
                    "  3. 重启 GameServer: docker compose restart gameserver\n\n"
                    "获取 API Key: https://platform.deepseek.com/"
                ),
                "actions": [],
                "state_changes": {},
            }
            return

        # Check if this is the first message (before saving)
        history = await state_service.get_recent_messages(player_id, count=1)
        is_first_message = len(history) == 0

        # Save user message
        await state_service.push_message(player_id, "user", message)
        logger.debug("trace=%s step=message_save role=user is_first=%s", trace_id, is_first_message)

        # Scene classification for dynamic pruning
        scene_keywords = self._settings.game.scene_keywords if self._settings.game.scene_keywords else None
        scene = classify_scene(message, scene_keywords, trace_id=trace_id)
        pruned_tools = prune_tools(GAME_TOOLS, scene)

        # RAG retrieval: query ChromaDB for relevant context
        rag_chunks = None
        rag_start = time.time()
        try:
            state_for_rag = await state_service.load_player_state(player_id)
            current_floor = int(state_for_rag.get("current_floor", 1)) if state_for_rag else None
            rag_entity_type = get_rag_entity_type(scene)
            from gameserver.db.chromadb_client import query_novels, query_entities
            # Scene-aware RAG: prioritize relevant entity type
            novel_chunks = query_novels(message, n_results=3, floor_filter=current_floor, trace_id=trace_id)
            entity_chunks = query_entities(
                message, n_results=3,
                entity_type=rag_entity_type,
                floor_filter=current_floor,
                trace_id=trace_id,
            )
            all_rag = []
            for r in novel_chunks:
                all_rag.append((r["distance"], f"[小说参考] {r['text']}"))
            for r in entity_chunks:
                etype = r["metadata"].get("entity_type", "unknown")
                all_rag.append((r["distance"], f"[{etype}数据] {r['text']}"))
            all_rag.sort(key=lambda x: x[0])
            rag_chunks = [text for _, text in all_rag] or None
            
            # Record RAG metrics
            rag_latency_ms = (time.time() - rag_start) * 1000
            chunks_count = len(all_rag)
            top_score = all_rag[0][0] if all_rag else 0.0
            metrics.add_rag_result(chunks_count=chunks_count, top_score=top_score, latency_ms=rag_latency_ms)
        except Exception as e:
            rag_latency_ms = (time.time() - rag_start) * 1000
            metrics.add_rag_result(chunks_count=0, top_score=0.0, latency_ms=rag_latency_ms, success=False, error=str(e))
            logger.warning("trace=%s step=rag_retrieve status=error error=%s latency_ms=%.1f", trace_id, e, rag_latency_ms)

        # Build context (3-layer memory + RAG + pruned tools)
        ctx = await build_context(
            player_id, message, pruned_tools,
            rag_chunks=rag_chunks, trace_id=trace_id,
            is_first_message=is_first_message
        )

        logger.info(
            "trace=%s step=game_start player=%s provider=%s msg=%s",
            trace_id,
            player_id,
            provider_name or self._settings.llm.default_provider,
            message[:100],
        )

        # ReAct loop
        all_actions: list[GameActionProto] = []
        state = await state_service.load_player_state(player_id)

        for round_idx in range(MAX_REACT_ROUNDS):
            # Call LLM with tools (with circuit breaker and retry)
            llm_start = time.time()
            response = None
            llm_error = None
            
            for retry in range(3):  # Max 3 retries
                try:
                    cb = get_circuit_breaker(provider_name or self._settings.llm.default_provider)
                    if not cb.can_execute():
                        logger.warning("trace=%s step=circuit_breaker status=open provider=%s", trace_id, provider_name)
                        # Try fallback provider if configured
                        fallback = self._get_fallback_provider(provider_name)
                        if fallback:
                            provider = fallback
                            continue
                        raise CircuitBreakerOpenError(f"Circuit breaker open for {provider_name}")
                    
                    response = await provider.chat_with_tools(
                        messages=[
                            ChatMessage(
                                role=m["role"],
                                content=m.get("content"),
                                tool_calls=m.get("tool_calls"),
                                tool_call_id=m.get("tool_call_id"),
                            )
                            for m in ctx.messages
                        ],
                        tools=ctx.tools,
                        trace_id=trace_id,
                    )
                    cb.record_success()
                    llm_error = None
                    break
                except CircuitBreakerOpenError:
                    raise
                except Exception as e:
                    llm_error = e
                    cb.record_failure()
                    if retry < 2:
                        wait_time = 2 ** retry  # Exponential backoff: 1s, 2s
                        logger.warning("trace=%s step=llm_call status=retry retry=%d wait_ms=%d error=%s", trace_id, retry + 1, wait_time * 1000, e)
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("trace=%s step=llm_call status=error error=%s", trace_id, e)
            
            if llm_error:
                # Fallback to simple chat if tool calling fails
                logger.warning("trace=%s step=llm_call status=fallback error=%s", trace_id, llm_error)
                break
            
            # Record LLM metrics with actual token usage from response
            llm_latency_ms = (time.time() - llm_start) * 1000
            # Get actual token counts from LLMResponse
            input_tokens = getattr(response, 'input_tokens', 0) or 0
            output_tokens = getattr(response, 'output_tokens', 0) or 0
            model_name = getattr(provider, '_config', None)
            model_name = model_name.model if model_name else 'unknown'
            metrics.add_llm_call(
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=llm_latency_ms,
                provider=provider_name or self._settings.llm.default_provider,
            )

            if not response or not hasattr(response, "tool_calls") or not response.tool_calls:
                break

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    tool_args = {}

                logger.info("trace=%s step=tool_dispatch tool=%s args=%s", trace_id, tool_name, str(tool_args)[:100])
                
                tool_start = time.time()
                result = await self._executor.execute(player_id, state, tool_name, tool_args, trace_id=trace_id)
                tool_latency_ms = (time.time() - tool_start) * 1000
                
                metrics.add_tool_call(tool=tool_name, latency_ms=tool_latency_ms, success=result.success, error=result.error)
                
                logger.info("trace=%s step=tool_complete tool=%s success=%s latency_ms=%d", trace_id, tool_name, result.success, int(tool_latency_ms))

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
        messages = [
            ChatMessage(
                role=m["role"],
                content=m.get("content") or "",
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
            )
            for m in ctx.messages
        ]

        stream_start = time.time()
        try:
            async for chunk in provider.stream_chat(messages):
                narrative_parts.append(chunk)
                yield {
                    "content": chunk,
                    "is_done": False,
                    "actions": [],
                    "state_changes": {},
                }
            stream_latency_ms = (time.time() - stream_start) * 1000
            logger.info("trace=%s step=stream_complete latency_ms=%.1f", trace_id, stream_latency_ms)
        except Exception as e:
            stream_latency_ms = (time.time() - stream_start) * 1000
            logger.error("trace=%s step=stream_error error=%s latency_ms=%.1f", trace_id, e, stream_latency_ms, exc_info=True)
            yield {"content": "", "is_done": True, "error": str(e), "actions": [], "state_changes": {}}
            return

        # Save assistant message
        full_narrative = "".join(narrative_parts)
        if full_narrative:
            await state_service.push_message(player_id, "assistant", full_narrative)
            logger.debug("trace=%s step=message_save role=assistant length=%d", trace_id, len(full_narrative))

        # Compress history if needed
        try:
            await maybe_compress_history(player_id, provider, trace_id=trace_id)
        except Exception as e:
            logger.warning("trace=%s step=history_compress error=%s", trace_id, e)

        # Log request summary and check for slow request
        metrics.log_summary(player_id)
        metrics.check_slow_request()
        
        logger.info("trace=%s step=game_complete player=%s actions=%d", trace_id, player_id, len(all_actions))
        
        # Final done message with all actions
        yield {
            "content": "",
            "is_done": True,
            "actions": all_actions,
            "state_changes": {},
        }
