"""Integration tests for the ReAct execution loop using a mock LLM provider."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from praxis_ai.core.agent.react_loop import ReActController
from praxis_ai.core.agent.types import (
    AgentMessage,
    AgentResponse,
    StreamChunk,
    ToolCall,
)
from praxis_ai.core.config.permissions import PermissionManager, PermissionMode
from praxis_ai.core.config.settings import Settings
from praxis_ai.core.providers.base import BaseLLMProvider
from praxis_ai.core.tools.registry import ToolRegistry


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider that simulates multi-turn reasoning and tool calls."""

    def __init__(self):
        self.call_count = 0

    async def stream_chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        on_chunk: Callable[[StreamChunk], None] | None = None,
    ) -> AgentResponse:
        self.call_count += 1

        if self.call_count == 1:
            # Turn 1: Emit a tool call to write a file
            tc = ToolCall(
                id="mock_call_1",
                name="write_file",
                arguments={
                    "path": "react_test.txt",
                    "content": "Autonomous ReAct Output",
                },
            )
            return AgentResponse(
                content="I will create the test file.",
                tool_calls=[tc],
            )
        elif self.call_count == 2:
            # Turn 2: Verify tool result was observed and produce final answer
            last_msg = messages[-1]
            assert last_msg.role == "tool"
            assert "react_test.txt" in last_msg.content

            return AgentResponse(
                content="The file `react_test.txt` has been created successfully!",
                tool_calls=[],
            )
        else:
            return AgentResponse(content="Done.", tool_calls=[])

    async def count_tokens(
        self, text_or_messages: str | list[AgentMessage], model: str | None = None
    ) -> int:
        return 50


@pytest.mark.asyncio
async def test_react_multi_turn_loop(tmp_path: Path):
    settings = Settings(
        workspace_dir=str(tmp_path),
        permission_mode="autonomous",
    )
    mock_provider = MockLLMProvider()
    tools = ToolRegistry.create_default_registry()
    permissions = PermissionManager(PermissionMode.AUTONOMOUS)

    controller = ReActController(
        settings=settings,
        provider=mock_provider,
        tools=tools,
        permission_manager=permissions,
    )

    final_answer = await controller.execute_turn("Please write a test file.")
    assert "react_test.txt" in final_answer
    assert mock_provider.call_count == 2

    # Check that file was created on disk by the tool
    created_file = tmp_path / "react_test.txt"
    assert created_file.exists()
    assert created_file.read_text() == "Autonomous ReAct Output"
