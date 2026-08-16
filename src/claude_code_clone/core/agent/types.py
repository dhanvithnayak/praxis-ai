"""Core types and Pydantic models for Agent state, tool calls, and streaming."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    """Represents a function/tool call requested by the LLM."""
    name: str
    arguments: str  # JSON string or raw accumulator during streaming


class ToolCall(BaseModel):
    """Represents a complete tool call with parsed arguments."""
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of executing a tool."""
    tool_call_id: str
    tool_name: str
    output: str
    is_error: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    """Standard message in the conversation history."""
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # Tool name for tool role


class StreamChunk(BaseModel):
    """Incremental chunk received during streaming inference."""
    delta_content: str | None = None
    tool_call_chunks: list[dict[str, Any]] | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class AgentResponse(BaseModel):
    """Final output from a single LLM generation turn."""
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
