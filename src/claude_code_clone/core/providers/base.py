"""Base LLM Provider interface definition."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from claude_code_clone.core.agent.types import AgentMessage, AgentResponse, StreamChunk


class BaseLLMProvider(ABC):
    """Abstract interface for LLM model providers."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        on_chunk: Callable[[StreamChunk], None] | None = None,
    ) -> AgentResponse:
        """Streams chat completions, invokes on_chunk callback, and returns the accumulated response."""
        ...

    @abstractmethod
    async def count_tokens(
        self, text_or_messages: str | list[AgentMessage], model: str | None = None
    ) -> int:
        """Calculates or estimates the token count for given text or messages."""
        ...
