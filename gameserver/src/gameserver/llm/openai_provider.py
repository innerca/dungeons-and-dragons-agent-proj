import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from gameserver.llm.base import ChatMessage, LLMProvider, LLMResponse
from gameserver.config.settings import ProviderConfig

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (OpenAI, DeepSeek, Ollama, etc.)."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None,
        )

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict]:
        result = []
        for m in messages:
            msg: dict = {"role": m.role, "content": m.content}
            if m.tool_calls is not None:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id is not None:
                msg["tool_call_id"] = m.tool_call_id
            result.append(msg)
        return result

    async def stream_chat(
        self, messages: list[ChatMessage], trace_id: str = "no-trace"
    ) -> AsyncIterator[str]:
        start_time = time.time()
        msgs = self._format_messages(messages)
        
        try:
            stream = await self._client.chat.completions.create(
                model=self._config.model,
                messages=msgs,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                stream=True,
            )
            
            chunk_count = 0
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    chunk_count += 1
                    yield delta.content
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "trace=%s step=llm_stream provider=openai model=%s chunks=%d latency_ms=%.1f",
                trace_id, self._config.model, chunk_count, latency_ms
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "trace=%s step=llm_stream provider=openai model=%s status=error error=%s latency_ms=%.1f",
                trace_id, self._config.model, e, latency_ms
            )
            raise

    async def chat(self, messages: list[ChatMessage]) -> str:
        msgs = self._format_messages(messages)
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=msgs,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict], trace_id: str = "no-trace"
    ) -> LLMResponse:
        """Call LLM with function/tool definitions for ReAct."""
        start_time = time.time()
        msgs = self._format_messages(messages)
        
        try:
            response = await self._client.chat.completions.create(
                model=self._config.model,
                messages=msgs,
                tools=tools if tools else None,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            msg = response.choices[0].message
            
            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            
            logger.info(
                "trace=%s step=llm_call provider=openai model=%s input_tokens=%d output_tokens=%d latency_ms=%.1f",
                trace_id, self._config.model, input_tokens, output_tokens, latency_ms
            )
            
            return LLMResponse(
                content=msg.content,
                tool_calls=msg.tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "trace=%s step=llm_call provider=openai model=%s status=error error=%s latency_ms=%.1f",
                trace_id, self._config.model, e, latency_ms
            )
            raise
