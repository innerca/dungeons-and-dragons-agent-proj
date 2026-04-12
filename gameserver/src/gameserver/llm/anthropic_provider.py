import logging
import time
from collections.abc import AsyncIterator

import anthropic

from gameserver.llm.base import ChatMessage, LLMProvider, LLMResponse
from gameserver.config.settings import ProviderConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(api_key=config.api_key)

    async def stream_chat(
        self, messages: list[ChatMessage], trace_id: str = "no-trace"
    ) -> AsyncIterator[str]:
        start_time = time.time()
        
        # Anthropic requires system message separately
        system_msg = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        try:
            chunk_count = 0
            async with self._client.messages.stream(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system_msg if system_msg else anthropic.NOT_GIVEN,
                messages=chat_msgs,
            ) as stream:
                async for text in stream.text_stream:
                    chunk_count += 1
                    yield text
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "trace=%s step=llm_stream provider=anthropic model=%s chunks=%d latency_ms=%.1f",
                trace_id, self._config.model, chunk_count, latency_ms
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "trace=%s step=llm_stream provider=anthropic model=%s status=error error=%s latency_ms=%.1f",
                trace_id, self._config.model, e, latency_ms
            )
            raise

    async def chat(self, messages: list[ChatMessage], trace_id: str = "no-trace") -> str:
        start_time = time.time()
        
        system_msg = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        try:
            response = await self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system_msg if system_msg else anthropic.NOT_GIVEN,
                messages=chat_msgs,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0
            
            logger.info(
                "trace=%s step=llm_call provider=anthropic model=%s input_tokens=%d output_tokens=%d latency_ms=%.1f",
                trace_id, self._config.model, input_tokens, output_tokens, latency_ms
            )
            
            return response.content[0].text if response.content else ""
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "trace=%s step=llm_call provider=anthropic model=%s status=error error=%s latency_ms=%.1f",
                trace_id, self._config.model, e, latency_ms
            )
            raise
    
    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict], trace_id: str = "no-trace"
    ) -> LLMResponse:
        """Call LLM with function/tool definitions for ReAct."""
        start_time = time.time()
        
        system_msg = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})
        
        # Convert OpenAI tool format to Anthropic format
        anthropic_tools = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
        
        try:
            response = await self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system_msg if system_msg else anthropic.NOT_GIVEN,
                messages=chat_msgs,
                tools=anthropic_tools if anthropic_tools else anthropic.NOT_GIVEN,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0
            
            logger.info(
                "trace=%s step=llm_call provider=anthropic model=%s input_tokens=%d output_tokens=%d latency_ms=%.1f",
                trace_id, self._config.model, input_tokens, output_tokens, latency_ms
            )
            
            # Convert Anthropic tool_use to OpenAI-style tool_calls
            tool_calls = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append(type('ToolCall', (), {
                        'id': block.id,
                        'function': type('Function', (), {
                            'name': block.name,
                            'arguments': str(block.input),
                        })(),
                    })())
            
            return LLMResponse(
                content=response.content[0].text if response.content and response.content[0].type == "text" else None,
                tool_calls=tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "trace=%s step=llm_call provider=anthropic model=%s status=error error=%s latency_ms=%.1f",
                trace_id, self._config.model, e, latency_ms
            )
            raise
