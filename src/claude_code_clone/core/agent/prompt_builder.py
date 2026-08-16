"""Dynamic system prompt builder and environment context assembler."""

import platform
import subprocess
from pathlib import Path

from claude_code_clone.core.agent.repo_map import RepoMapGenerator
from claude_code_clone.core.config.settings import Settings


def get_git_branch(workspace_dir: Path) -> str | None:
    """Gets the active git branch name if inside a git repository."""
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


class PromptBuilder:
    """Constructs dynamic system prompts injected into the ReAct loop."""

    @classmethod
    def build_system_prompt(
        cls,
        settings: Settings,
        rag_context: str | None = None,
        custom_instructions: str | None = None,
    ) -> str:
        workspace = Path(settings.workspace_dir).resolve()
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        git_branch = get_git_branch(workspace) or "Not a git repo or detached HEAD"

        repo_map = RepoMapGenerator.generate_summary(workspace)

        prompt_sections = [
            "# Identity & Purpose",
            "You are an expert, autonomous AI coding assistant with deep engineering capabilities (a multi-provider Claude Code clone).",
            "You help users inspect, navigate, write, debug, test, and automate code in their repository using the ReAct (Reasoning and Acting) paradigm.",
            "",
            "# Environment & Workspace Context",
            f"- **Operating System**: {os_info}",
            f"- **Workspace Root**: `{workspace}`",
            f"- **Active Git Branch**: `{git_branch}`",
            f"- **Python Version**: {platform.python_version()}",
            "",
            "# Workspace File Overview (Repo Map)",
            f"```text\n{repo_map}\n```",
            "",
            "# Operational Guidelines & ReAct Execution Rules",
            "1. **Explore Before Modifying**: When answering questions or fixing bugs, first use `list_dir`, `grep_search`, `file_glob`, or `read_file` to understand the codebase context.",
            "2. **Precise File Editing**: Prefer `edit_file` with precise `target_content` blocks over rewriting entire files with `write_file` whenever modifying existing code.",
            "3. **Run Commands Safely**: Use `bash_executor` to execute tests, builds, linting, or scripts. Avoid destructive commands unless explicitly asked.",
            "4. **Enterprise Institutional Memory (RAG)**: If an enterprise RAG tool (`query_knowledge_base`) is available and you encounter questions regarding internal infrastructure, deploy pipelines, architectures, or company standards, query the knowledge base to retrieve established organizational context.",
            "5. **Honesty & Conciseness**: Be concise, actionable, and transparent about your actions.",
        ]

        if rag_context:
            prompt_sections.extend(
                [
                    "",
                    "# Enterprise Context (Pre-loaded RAG knowledge)",
                    rag_context,
                ]
            )

        if custom_instructions:
            prompt_sections.extend(
                [
                    "",
                    "# Custom Project Instructions",
                    custom_instructions,
                ]
            )

        return "\n".join(prompt_sections)
