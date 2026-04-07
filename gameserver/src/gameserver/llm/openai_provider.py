import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from gameserver.llm.base import ChatMessage, LLMProvider
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
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        msgs = self._format_messages(messages)
        stream = await self._client.chat.completions.create(
            model=self._config.model,
            messages=msgs,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

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
        self, messages: list[ChatMessage], tools: list[dict]
    ) -> Any:
        """Call LLM with function/tool definitions for ReAct."""
        msgs = self._format_messages(messages)
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=msgs,
            tools=tools if tools else None,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        return response.choices[0].message
