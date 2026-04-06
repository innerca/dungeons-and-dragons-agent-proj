from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Strategy interface)."""

    @abstractmethod
    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        """Stream chat completion, yielding text chunks."""
        ...

    @abstractmethod
    async def chat(self, messages: list[ChatMessage]) -> str:
        """Non-streaming chat completion."""
        ...

    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict]
    ) -> Any:
        """Chat with function/tool calling support. Returns raw response.

        Default implementation raises AttributeError (provider doesn't support tools).
        """
        raise AttributeError(f"{self.__class__.__name__} does not support tool calling")
