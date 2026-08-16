"""Central tool registry and schema generator."""

from typing import Any

from claude_code_clone.core.agent.types import ToolCall, ToolResult
from claude_code_clone.core.tools.base import BaseTool, ExecutionContext
from claude_code_clone.core.tools.bash import BashExecutorTool
from claude_code_clone.core.tools.file_system import (
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from claude_code_clone.core.tools.git import GitTool
from claude_code_clone.core.tools.rag_tool import QueryKnowledgeBaseTool
from claude_code_clone.core.tools.search import FileGlobTool, GrepSearchTool


class ToolRegistry:
    """Manages available agent tools, schema generation, and execution routing."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Retrieves a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Returns all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Generates OpenAI / LiteLLM function calling schemas for all registered tools."""
        return [tool.get_json_schema() for tool in self._tools.values()]

    async def execute_call(
        self,
        tool_call: ToolCall,
        context: ExecutionContext,
    ) -> ToolResult:
        """Routes and executes a ToolCall, ensuring error recovery and schema compliance."""
        tool = self._tools.get(tool_call.name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                output=f"Error: Tool '{tool_call.name}' is not recognized or available.",
                is_error=True,
            )

        try:
            # Validate and execute
            result = await tool.execute(tool_call.arguments, context)
            # Ensure tool_call_id and tool_name match the invocation
            result.tool_call_id = tool_call.id
            result.tool_name = tool_call.name
            return result
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                output=f"Execution error in '{tool_call.name}': {e}",
                is_error=True,
            )

    @classmethod
    def create_default_registry(cls) -> "ToolRegistry":
        """Factory initializing standard coding and workspace tools."""
        registry = cls()
        registry.register(ReadFileTool())
        registry.register(WriteFileTool())
        registry.register(EditFileTool())
        registry.register(ListDirTool())
        registry.register(GrepSearchTool())
        registry.register(FileGlobTool())
        registry.register(BashExecutorTool())
        registry.register(GitTool())
        registry.register(QueryKnowledgeBaseTool())
        return registry
