import logging
from collections.abc import AsyncIterator

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

    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
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
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=msgs,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        return response.choices[0].message.content or ""
