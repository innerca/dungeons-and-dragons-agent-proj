from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """Standardized LLM response with token usage info."""
    content: str | None = None
    tool_calls: list[Any] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Strategy interface)."""

    @abstractmethod
    async def stream_chat(
        self, messages: list[ChatMessage], trace_id: str = "no-trace"
    ) -> AsyncIterator[str]:
        """Stream chat completion, yielding text chunks."""
        ...

    @abstractmethod
    async def chat(self, messages: list[ChatMessage]) -> str:
        """Non-streaming chat completion."""
        ...

    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict], trace_id: str = "no-trace"
    ) -> LLMResponse:
        """Chat with function/tool calling support. Returns LLMResponse.

        Default implementation raises AttributeError (provider doesn't support tools).
        """
        raise AttributeError(f"{self.__class__.__name__} does not support tool calling")
