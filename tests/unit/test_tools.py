"""Unit tests for file system, search, bash tools, and registry."""

from pathlib import Path

import pytest

from claude_code_clone.core.agent.types import ToolCall
from claude_code_clone.core.tools.base import ExecutionContext
from claude_code_clone.core.tools.bash import BashExecutorTool
from claude_code_clone.core.tools.file_system import (
    EditFileTool,
    ReadFileTool,
    WriteFileTool,
)
from claude_code_clone.core.tools.registry import ToolRegistry
from claude_code_clone.core.tools.search import FileGlobTool, GrepSearchTool


@pytest.fixture
def workspace(tmp_path: Path) -> ExecutionContext:
    return ExecutionContext(workspace_dir=tmp_path)


@pytest.mark.asyncio
async def test_file_write_and_read(workspace: ExecutionContext):
    write_tool = WriteFileTool()
    read_tool = ReadFileTool()

    # 1. Write file
    write_res = await write_tool.execute(
        {"path": "subdir/test.txt", "content": "Line 1\nLine 2\nLine 3\n"},
        workspace,
    )
    assert not write_res.is_error
    assert "created file" in write_res.output.lower()

    # 2. Read whole file
    read_res = await read_tool.execute({"path": "subdir/test.txt"}, workspace)
    assert not read_res.is_error
    assert "Line 1" in read_res.output
    assert "Line 3" in read_res.output

    # 3. Read slice
    slice_res = await read_tool.execute(
        {"path": "subdir/test.txt", "start_line": 2, "end_line": 2}, workspace
    )
    assert not slice_res.is_error
    assert "Line 2" in slice_res.output
    assert "Line 1" not in slice_res.output


@pytest.mark.asyncio
async def test_edit_file_tool(workspace: ExecutionContext):
    write_tool = WriteFileTool()
    edit_tool = EditFileTool()

    await write_tool.execute(
        {"path": "code.py", "content": "def add(a, b):\n    return a - b\n"},
        workspace,
    )

    # Apply edit
    edit_res = await edit_tool.execute(
        {
            "path": "code.py",
            "target_content": "    return a - b",
            "replacement_content": "    return a + b",
        },
        workspace,
    )
    assert not edit_res.is_error
    assert "Successfully replaced 1 occurrence" in edit_res.output

    # Verify updated content
    updated = (workspace.workspace_dir / "code.py").read_text()
    assert "return a + b" in updated


@pytest.mark.asyncio
async def test_grep_and_glob(workspace: ExecutionContext):
    write_tool = WriteFileTool()
    await write_tool.execute(
        {"path": "src/main.py", "content": "print('hello universe')\n"}, workspace
    )
    await write_tool.execute(
        {"path": "src/util.py", "content": "SECRET_KEY = 'xyz'\n"}, workspace
    )

    grep_tool = GrepSearchTool()
    grep_res = await grep_tool.execute({"query": "SECRET_KEY"}, workspace)
    assert not grep_res.is_error
    assert "SECRET_KEY" in grep_res.output
    assert "src/util.py" in grep_res.output

    glob_tool = FileGlobTool()
    glob_res = await glob_tool.execute({"pattern": "**/*.py"}, workspace)
    assert not glob_res.is_error
    assert "src/main.py" in glob_res.output
    assert "src/util.py" in glob_res.output


@pytest.mark.asyncio
async def test_bash_executor(workspace: ExecutionContext):
    bash_tool = BashExecutorTool()
    res = await bash_tool.execute({"command": "echo 'Testing Bash 123'"}, workspace)
    assert not res.is_error
    assert "Testing Bash 123" in res.output
    assert "[Exit code: 0]" in res.output


@pytest.mark.asyncio
async def test_tool_registry(workspace: ExecutionContext):
    registry = ToolRegistry.create_default_registry()
    schemas = registry.get_schemas()
    assert len(schemas) >= 7

    # Verify tool call execution
    tool_call = ToolCall(
        id="call_test_1",
        name="write_file",
        arguments={"path": "registry_test.txt", "content": "Registry works!"},
    )
    result = await registry.execute_call(tool_call, workspace)
    assert result.tool_call_id == "call_test_1"
    assert not result.is_error
    assert (workspace.workspace_dir / "registry_test.txt").exists()
