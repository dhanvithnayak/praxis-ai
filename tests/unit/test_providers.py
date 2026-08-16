"""Unit tests for LiteLLM Gateway and model resolution."""

import pytest

from claude_code_clone.core.agent.types import AgentMessage, ToolCall
from claude_code_clone.core.config.settings import Settings
from claude_code_clone.core.providers.gateway import LiteLLMGateway
from claude_code_clone.core.providers.models import resolve_model_name


def test_model_alias_resolution():
    assert (
        resolve_model_name("claude-3-7-sonnet")
        == "anthropic/claude-3-7-sonnet-20250219"
    )
    assert resolve_model_name("gpt-4o") == "openai/gpt-4o"
    assert resolve_model_name("gemini-flash") == "gemini/gemini-2.5-flash"
    assert resolve_model_name("deepseek-r1") == "ollama/deepseek-r1:14b"
    assert (
        resolve_model_name("custom/my-fine-tuned-model") == "custom/my-fine-tuned-model"
    )


def test_gateway_message_formatting():
    settings = Settings(model="anthropic/claude-3-7-sonnet-20250219")
    gateway = LiteLLMGateway(settings=settings)

    messages = [
        AgentMessage(role="system", content="You are a helpful coding assistant."),
        AgentMessage(role="user", content="List directory contents"),
        AgentMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(id="call_123", name="list_dir", arguments={"path": "."})
            ],
        ),
        AgentMessage(
            role="tool",
            content='["file1.txt", "file2.py"]',
            tool_call_id="call_123",
            name="list_dir",
        ),
    ]

    formatted = gateway._format_messages_for_provider(messages)
    assert len(formatted) == 4
    assert formatted[0]["role"] == "system"
    assert formatted[1]["role"] == "user"
    assert formatted[2]["role"] == "assistant"
    assert "tool_calls" in formatted[2]
    assert formatted[2]["tool_calls"][0]["function"]["name"] == "list_dir"
    assert formatted[3]["role"] == "tool"
    assert formatted[3]["tool_call_id"] == "call_123"


@pytest.mark.asyncio
async def test_token_counter():
    gateway = LiteLLMGateway()
    tokens = await gateway.count_tokens("Hello, world! This is a test.")
    assert tokens > 0
