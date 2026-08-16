"""Base Tool interface and ExecutionContext definition."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from claude_code_clone.core.agent.types import ToolResult


class ExecutionContext(BaseModel):
    """Context provided to a tool during execution."""

    workspace_dir: Path = Field(default_factory=Path.cwd)
    session_id: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str
    description: str
    is_destructive: bool = False
    args_schema: type[BaseModel]

    @abstractmethod
    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        """Executes the tool with validated parameters."""
        ...

    def get_json_schema(self) -> dict[str, Any]:
        """Generates OpenAI/LiteLLM compatible JSONSchema for this tool."""
        schema = self.args_schema.model_json_schema()
        # Clean up pydantic internal titles if present
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }
