"""ReAct (Reasoning + Acting) execution loop controller."""

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from claude_code_clone.core.agent.context_manager import ContextManager
from claude_code_clone.core.agent.prompt_builder import PromptBuilder
from claude_code_clone.core.agent.types import (
    AgentMessage,
    AgentResponse,
    StreamChunk,
    ToolCall,
    ToolResult,
)
from claude_code_clone.core.config.permissions import PermissionManager, PermissionMode
from claude_code_clone.core.config.settings import Settings
from claude_code_clone.core.providers.base import BaseLLMProvider
from claude_code_clone.core.providers.gateway import LiteLLMGateway
from claude_code_clone.core.tools.base import ExecutionContext
from claude_code_clone.core.tools.registry import ToolRegistry


class ReActEvents:
    """Event hooks for UI rendering during the ReAct loop."""

    on_token: Callable[[str], None] | None = None
    on_tool_call_start: Callable[[ToolCall], None] | None = None
    on_tool_call_confirm: (
        Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool]] | None
    ) = None
    on_tool_call_result: Callable[[ToolResult], None] | None = None
    on_turn_complete: Callable[[AgentResponse], None] | None = None


class ReActController:
    """Orchestrates the Reasoning and Acting execution cycle."""

    def __init__(
        self,
        settings: Settings | None = None,
        provider: BaseLLMProvider | None = None,
        tools: ToolRegistry | None = None,
        permission_manager: PermissionManager | None = None,
        custom_instructions: str | None = None,
    ) -> None:
        self.settings = settings or Settings.load()
        self.provider = provider or LiteLLMGateway(self.settings)
        self.tools = tools or ToolRegistry.create_default_registry()
        self.permission_manager = permission_manager or PermissionManager(
            PermissionMode(self.settings.permission_mode)
        )
        self.context_manager = ContextManager(self.settings)
        self.workspace_dir = Path(self.settings.workspace_dir)

        # Initialize conversation with system prompt
        self.system_prompt = PromptBuilder.build_system_prompt(
            self.settings,
            custom_instructions=custom_instructions,
        )
        self.history: list[AgentMessage] = [
            AgentMessage(role="system", content=self.system_prompt)
        ]

    def reset_history(self) -> None:
        """Clears conversation history and re-inserts the fresh system prompt."""
        self.history = [AgentMessage(role="system", content=self.system_prompt)]

    async def execute_turn(
        self,
        user_input: str,
        events: ReActEvents | None = None,
        max_iterations: int = 25,
    ) -> str:
        """
        Runs a complete multi-turn ReAct reasoning and tool-execution loop for the given user input.
        Returns the final assistant text response.
        """
        # Append user input
        self.history.append(AgentMessage(role="user", content=user_input))
        iteration = 0
        final_answer = ""

        while iteration < max_iterations:
            iteration += 1

            # Prune and compact context if getting close to token limit
            self.history = self.context_manager.prune_and_compact_if_needed(
                self.history
            )

            # Prepare schemas
            tool_schemas = self.tools.get_schemas() if self.tools else None

            # Stream callback handler
            def _handle_chunk(chunk: StreamChunk) -> None:
                if chunk.delta_content and events and events.on_token:
                    events.on_token(chunk.delta_content)

            # Call LLM
            response: AgentResponse = await self.provider.stream_chat(
                messages=self.history,
                tools=tool_schemas,
                model=self.settings.model,
                temperature=self.settings.temperature,
                on_chunk=_handle_chunk,
            )

            if events and events.on_turn_complete:
                events.on_turn_complete(response)

            # Record assistant turn in history
            assistant_msg = AgentMessage(
                role="assistant",
                content=response.content if response.content else None,
                tool_calls=response.tool_calls if response.tool_calls else None,
            )
            self.history.append(assistant_msg)

            # If no tool calls were requested, the model produced its final answer
            if not response.tool_calls:
                final_answer = response.content
                break

            # Execute requested tool calls
            for tool_call in response.tool_calls:
                if events and events.on_tool_call_start:
                    events.on_tool_call_start(tool_call)

                # Check safety & permissions
                tool_instance = self.tools.get(tool_call.name)
                is_destructive = tool_instance.is_destructive if tool_instance else True
                needs_confirm, reason = self.permission_manager.should_ask_confirmation(
                    tool_call.name,
                    is_destructive=is_destructive,
                    params=tool_call.arguments,
                )

                approved = True
                if needs_confirm and events and events.on_tool_call_confirm:
                    prompt_reason = reason or f"Run tool '{tool_call.name}'"
                    approved = await events.on_tool_call_confirm(
                        prompt_reason, tool_call.arguments
                    )

                if not approved:
                    tool_result = ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        output=f"User rejected or cancelled execution of tool '{tool_call.name}'.",
                        is_error=True,
                    )
                else:
                    exec_context = ExecutionContext(workspace_dir=self.workspace_dir)
                    tool_result = await self.tools.execute_call(tool_call, exec_context)

                if events and events.on_tool_call_result:
                    events.on_tool_call_result(tool_result)

                # Inject observation into conversation history
                self.history.append(
                    AgentMessage(
                        role="tool",
                        content=tool_result.output,
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                )

        return final_answer
