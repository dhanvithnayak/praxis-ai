"""Search tools: grep_search and file_glob."""

import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from praxis_ai.core.agent.types import ToolResult
from praxis_ai.core.tools.base import BaseTool, ExecutionContext
from praxis_ai.core.tools.file_system import IGNORE_PATTERNS


class GrepSearchArgs(BaseModel):
    query: str = Field(
        description="The regular expression or string pattern to search for"
    )
    path: str = Field(
        default=".", description="The directory or file path to search within"
    )
    case_sensitive: bool = Field(
        default=False, description="Whether search should be case-sensitive"
    )
    max_results: int = Field(
        default=50, description="Maximum number of matching lines to return"
    )


class GrepSearchTool(BaseTool):
    name = "grep_search"
    description = "Searches for text or regex patterns across files in the workspace, returning matching lines."
    is_destructive = False
    args_schema = GrepSearchArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = GrepSearchArgs(**params)
            search_root = Path(args.path)
            if not search_root.is_absolute():
                search_root = context.workspace_dir / search_root

            if not search_root.exists():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Path '{args.path}' does not exist.",
                    is_error=True,
                )

            flags = 0 if args.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(args.query, flags)
            except re.error as e:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Invalid regex pattern '{args.query}': {e}",
                    is_error=True,
                )

            matches: list[str] = []
            files_to_search: list[Path] = []

            if search_root.is_file():
                files_to_search.append(search_root)
            else:
                for root, dirs, files in os.walk(search_root):
                    # Filter out ignored directories
                    dirs[:] = [
                        d
                        for d in dirs
                        if d not in IGNORE_PATTERNS and not d.startswith(".")
                    ]
                    for f in files:
                        if f not in IGNORE_PATTERNS and not f.startswith("."):
                            files_to_search.append(Path(root) / f)

            for file_path in files_to_search:
                if len(matches) >= args.max_results:
                    break
                try:
                    rel_path = file_path.relative_to(context.workspace_dir)
                except ValueError:
                    rel_path = file_path

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                for line_no, line in enumerate(content.splitlines(), start=1):
                    if pattern.search(line):
                        matches.append(f"{rel_path}:{line_no}: {line.strip()}")
                        if len(matches) >= args.max_results:
                            break

            if not matches:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"No matches found for pattern '{args.query}' in '{args.path}'.",
                )

            result_str = "\n".join(matches)
            if len(matches) >= args.max_results:
                result_str += f"\n\n(Truncated to {args.max_results} matches)"

            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Found {len(matches)} match(es) for '{args.query}':\n"
                + result_str,
                metadata={"match_count": len(matches)},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error during grep search: {e}",
                is_error=True,
            )


class FileGlobArgs(BaseModel):
    pattern: str = Field(
        description="Glob pattern to search for (e.g. '**/*.py', 'infra/**/*.tf')"
    )
    path: str = Field(default=".", description="Base directory to search from")


class FileGlobTool(BaseTool):
    name = "file_glob"
    description = "Finds all files matching a glob pattern relative to the workspace."
    is_destructive = False
    args_schema = FileGlobArgs

    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        try:
            args = FileGlobArgs(**params)
            base_dir = Path(args.path)
            if not base_dir.is_absolute():
                base_dir = context.workspace_dir / base_dir

            if not base_dir.exists() or not base_dir.is_dir():
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"Error: Directory '{args.path}' does not exist.",
                    is_error=True,
                )

            matched_files: list[str] = []
            for path in base_dir.glob(args.pattern):
                # Ignore noisy folders
                parts = path.parts
                if any(p in IGNORE_PATTERNS for p in parts):
                    continue
                try:
                    rel_path = str(path.relative_to(context.workspace_dir))
                except ValueError:
                    rel_path = str(path)
                matched_files.append(rel_path)

            matched_files.sort()

            if not matched_files:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"No files matched glob pattern '{args.pattern}' in '{args.path}'.",
                )

            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Matched {len(matched_files)} file(s) for '{args.pattern}':\n"
                + "\n".join(matched_files[:100]),
                metadata={"count": len(matched_files)},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error running file glob: {e}",
                is_error=True,
            )
