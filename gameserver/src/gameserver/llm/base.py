from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
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
