"""File system tools: read_file, write_file, edit_file, list_dir."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from claude_code_clone.core.agent.types import ToolResult
from claude_code_clone.core.tools.base import BaseTool, ExecutionContext
from claude_code_clone.utils.diff import apply_block_replacement, compute_unified_diff

IGNORE_PATTERNS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}


# ----------------------------------------------------------------------
# Read File Tool
# ----------------------------------------------------------------------
class ReadFileArgs(BaseModel):
    path: str = Field(
        description="The path to the file to read (relative to workspace or absolute)"
    )
    start_line: int | None = Field(
        default=None, description="Optional 1-indexed start line to read from"
    )
    end_line: int | None = Field(
        default=None, description="Optional 1-indexed end line (inclusive)"
    )


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads the content of a text file from the workspace, optionally between start_line and end_line."
    is_destructive = False
    args_schema = ReadFileArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = ReadFileArgs(**params)
            file_path = Path(args.path)
            if not file_path.is_absolute():
                file_path = context.workspace_dir / file_path

            if not file_path.exists():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: File '{args.path}' does not exist.",
                    is_error=True,
                )

            if not file_path.is_file():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Path '{args.path}' is a directory, not a file.",
                    is_error=True,
                )

            # Read text with fallback encoding
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: File '{args.path}' appears to be binary or not UTF-8 encoded.",
                    is_error=True,
                )

            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            start = (
                (args.start_line - 1) if args.start_line and args.start_line > 0 else 0
            )
            end = (
                args.end_line
                if args.end_line and args.end_line <= total_lines
                else total_lines
            )

            if start >= total_lines:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: start_line {args.start_line} exceeds total lines ({total_lines}).",
                    is_error=True,
                )

            selected_lines = lines[start:end]
            formatted_output = "".join(
                f"{i + start + 1:4d} | {line}" for i, line in enumerate(selected_lines)
            )

            header = f"[File: {args.path} (Lines {start + 1}-{end} of {total_lines})]\n"
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=header + formatted_output,
                metadata={
                    "total_lines": total_lines,
                    "lines_returned": len(selected_lines),
                },
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error reading file '{params.get('path')}': {e}",
                is_error=True,
            )


# ----------------------------------------------------------------------
# Write File Tool
# ----------------------------------------------------------------------
class WriteFileArgs(BaseModel):
    path: str = Field(
        description="The path to the file to create or overwrite (relative to workspace or absolute)"
    )
    content: str = Field(description="The complete content to write into the file")


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Creates a new file or overwrites an existing file with the provided content."
    )
    is_destructive = True
    args_schema = WriteFileArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = WriteFileArgs(**params)
            file_path = Path(args.path)
            if not file_path.is_absolute():
                file_path = context.workspace_dir / file_path

            file_path.parent.mkdir(parents=True, exist_ok=True)
            existed = file_path.exists()
            file_path.write_text(args.content, encoding="utf-8")

            action = "Overwrote" if existed else "Created"
            line_count = len(args.content.splitlines())
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Successfully {action.lower()} file '{args.path}' ({line_count} lines written).",
                metadata={
                    "path": str(file_path),
                    "lines": line_count,
                    "existed": existed,
                },
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error writing file '{params.get('path')}': {e}",
                is_error=True,
            )


# ----------------------------------------------------------------------
# Edit File Tool (Targeted Block Replacement with Diff)
# ----------------------------------------------------------------------
class EditFileArgs(BaseModel):
    path: str = Field(description="The path to the file to modify")
    target_content: str = Field(
        description="The EXACT existing text currently in the file to be replaced. Must match existing file content."
    )
    replacement_content: str = Field(
        description="The new text that will replace target_content."
    )
    allow_multiple: bool = Field(
        default=False,
        description="Set to true if multiple occurrences should be replaced",
    )


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Modifies an existing file by precisely replacing target_content with replacement_content."
    is_destructive = True
    args_schema = EditFileArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = EditFileArgs(**params)
            file_path = Path(args.path)
            if not file_path.is_absolute():
                file_path = context.workspace_dir / file_path

            if not file_path.exists():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: File '{args.path}' does not exist to edit.",
                    is_error=True,
                )

            original_content = file_path.read_text(encoding="utf-8")
            new_content, count = apply_block_replacement(
                original_content,
                args.target_content,
                args.replacement_content,
                allow_multiple=args.allow_multiple,
            )

            file_path.write_text(new_content, encoding="utf-8")
            diff = compute_unified_diff(
                original_content, new_content, from_file=args.path, to_file=args.path
            )

            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Successfully replaced {count} occurrence(s) in '{args.path}'.\n\n```diff\n{diff}\n```",
                metadata={"path": str(file_path), "replacements": count, "diff": diff},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error editing file '{params.get('path')}': {e}",
                is_error=True,
            )


# ----------------------------------------------------------------------
# List Directory Tool
# ----------------------------------------------------------------------
class ListDirArgs(BaseModel):
    path: str = Field(
        default=".",
        description="Path to directory to list (relative to workspace or absolute)",
    )
    recursive: bool = Field(
        default=False, description="Whether to recursively list subdirectories"
    )
    max_depth: int = Field(
        default=2, description="Maximum directory depth when recursive is true"
    )


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "Lists files and subdirectories within a given directory, respecting common ignore patterns."
    is_destructive = False
    args_schema = ListDirArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = ListDirArgs(**params)
            target_dir = Path(args.path)
            if not target_dir.is_absolute():
                target_dir = context.workspace_dir / target_dir

            if not target_dir.exists():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Directory '{args.path}' does not exist.",
                    is_error=True,
                )

            if not target_dir.is_dir():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Path '{args.path}' is a file, not a directory.",
                    is_error=True,
                )

            entries: list[str] = []

            def _traverse(current_dir: Path, current_depth: int, prefix: str = ""):
                if current_depth > args.max_depth:
                    return
                try:
                    items = sorted(
                        current_dir.iterdir(),
                        key=lambda p: (not p.is_dir(), p.name.lower()),
                    )
                except PermissionError:
                    return

                for item in items:
                    if item.name in IGNORE_PATTERNS or item.name.startswith(".git"):
                        continue
                    if item.is_dir():
                        entries.append(f"{prefix}📁 {item.name}/")
                        if args.recursive:
                            _traverse(item, current_depth + 1, prefix + "  ")
                    else:
                        entries.append(f"{prefix}📄 {item.name}")

            _traverse(target_dir, current_depth=1)

            if not entries:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Directory '{args.path}' is empty.",
                )

            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Contents of '{args.path}':\n" + "\n".join(entries),
                metadata={"count": len(entries)},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error listing directory '{params.get('path')}': {e}",
                is_error=True,
            )
