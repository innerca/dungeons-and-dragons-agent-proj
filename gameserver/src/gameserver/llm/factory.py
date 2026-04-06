from gameserver.config.settings import ProviderConfig
from gameserver.llm.base import LLMProvider
from gameserver.llm.openai_provider import OpenAICompatibleProvider
from gameserver.llm.anthropic_provider import AnthropicProvider

_PROVIDER_MAP: dict[str, type[LLMProvider]] = {
    "openai": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
}


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create(config: ProviderConfig) -> LLMProvider:
        provider_cls = _PROVIDER_MAP.get(config.provider_type)
        if provider_cls is None:
            raise ValueError(
                f"Unknown provider type: {config.provider_type}. "
                f"Available: {list(_PROVIDER_MAP.keys())}"
            )
        return provider_cls(config)
