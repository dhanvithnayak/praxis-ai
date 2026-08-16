"""Bash and shell execution tool."""

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from claude_code_clone.core.agent.types import ToolResult
from claude_code_clone.core.tools.base import BaseTool, ExecutionContext


class BashArgs(BaseModel):
    command: str = Field(description="The shell command line string to execute in bash")
    timeout_seconds: int = Field(
        default=60, description="Maximum execution timeout in seconds"
    )


class BashExecutorTool(BaseTool):
    name = "bash_executor"
    description = "Executes a command line instruction in a bash shell within the workspace, capturing stdout, stderr, and exit code."
    is_destructive = True
    args_schema = BashArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        args = BashArgs(**params)
        cmd_str = args.command.strip()
        cwd_dir = context.workspace_dir

        if not cmd_str:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output="Error: Empty command provided.",
                is_error=True,
            )

        try:
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd_dir),
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=float(args.timeout_seconds),
                )
            except TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Command timed out after {args.timeout_seconds} seconds.",
                    is_error=True,
                    metadata={"timeout": True},
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
            exit_code = process.returncode if process.returncode is not None else 0

            output_lines: list[str] = []
            if stdout:
                output_lines.append(stdout)
            if stderr:
                output_lines.append(f"[stderr]\n{stderr}")
            if not stdout and not stderr:
                output_lines.append(
                    f"(Command exited with code {exit_code}, no output produced)"
                )

            full_output = "\n\n".join(output_lines)
            is_error = exit_code != 0

            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"[Exit code: {exit_code}]\n{full_output}",
                is_error=is_error,
                metadata={"exit_code": exit_code, "command": cmd_str},
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error running command '{cmd_str}': {e}",
                is_error=True,
            )
