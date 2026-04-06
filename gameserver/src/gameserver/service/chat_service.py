import logging
from collections.abc import AsyncIterator

from gameserver.config.settings import Settings
from gameserver.llm.base import ChatMessage, LLMProvider
from gameserver.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


class ChatService:
    """Business logic layer for chat operations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, provider_name: str | None = None) -> LLMProvider:
        name = provider_name or self._settings.llm.default_provider
        if name not in self._providers:
            config = self._settings.llm.providers.get(name)
            if config is None:
                raise ValueError(
                    f"Provider '{name}' not found in config. "
                    f"Available: {list(self._settings.llm.providers.keys())}"
                )
            self._providers[name] = LLMProviderFactory.create(config)
            logger.info("Created LLM provider: %s (model=%s)", name, config.model)
        return self._providers[name]

    async def stream_chat(
        self,
        message: str,
        session_id: str = "",
        model: str = "",
    ) -> AsyncIterator[str]:
        """Process a chat message and stream LLM response."""
        # Determine which provider to use
        provider_name = None
        if model:
            # Check if model name matches a provider name
            if model in self._settings.llm.providers:
                provider_name = model

        provider = self._get_provider(provider_name)

        messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content=message),
        ]

        logger.info(
            "Chat request: session=%s, provider=%s, message=%s",
            session_id,
            provider_name or self._settings.llm.default_provider,
            message[:100],
        )

        async for chunk in provider.stream_chat(messages):
            yield chunk
