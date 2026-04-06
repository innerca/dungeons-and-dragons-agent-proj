import logging
from collections.abc import AsyncIterator

import anthropic

from gameserver.llm.base import ChatMessage, LLMProvider
from gameserver.config.settings import ProviderConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(api_key=config.api_key)

    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        # Anthropic requires system message separately
        system_msg = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        async with self._client.messages.stream(
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            system=system_msg if system_msg else anthropic.NOT_GIVEN,
            messages=chat_msgs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat(self, messages: list[ChatMessage]) -> str:
        system_msg = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        response = await self._client.messages.create(
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            system=system_msg if system_msg else anthropic.NOT_GIVEN,
            messages=chat_msgs,
        )
        return response.content[0].text if response.content else ""
