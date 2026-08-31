"""Git operations tool."""

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, Field

from praxis_ai.core.agent.types import ToolResult
from praxis_ai.core.tools.base import BaseTool, ExecutionContext


class GitArgs(BaseModel):
    subcommand: Literal["status", "diff", "log", "branch"] = Field(
        description="The git subcommand to run ('status', 'diff', 'log', 'branch')"
    )
    args: str | None = Field(
        default=None,
        description="Optional additional arguments for git (e.g. '--staged', '-n 5')",
    )


class GitTool(BaseTool):
    name = "git_manager"
    description = "Inspects Git repository state including status, staged/unstaged diffs, recent commit logs, and branches."
    is_destructive = False
    args_schema = GitArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = GitArgs(**params)
            cmd = f"git {args.subcommand}"
            if args.args:
                cmd += f" {args.args}"

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(context.workspace_dir),
            )
            stdout_bytes, stderr_bytes = await process.communicate()
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            if process.returncode != 0:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Git error (exit code {process.returncode}):\n{stderr or stdout}",
                    is_error=True,
                )

            output = stdout if stdout else f"(No output for '{cmd}')"
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=output,
                metadata={"command": cmd},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error executing git command: {e}",
                is_error=True,
            )
