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
            "1. **Read Before Editing (MANDATORY)**: Whenever asked to modify, append, edit, or refactor a file, you MUST FIRST call `read_file` to read the exact existing lines. NEVER guess or hallucinate `target_content`.",
            "2. **How to Edit Files**:",
            "   - `target_content`: The EXACT existing text currently in the file that you want to replace.",
            "   - `replacement_content`: The new text that will replace `target_content`.",
            "   - *Example*: If `read_file` shows line 1 is `# Project Title`, and you want to append `%` to line 1:",
            "     Call `edit_file(path='...', target_content='# Project Title', replacement_content='# Project Title%')`.",
            "3. **Direct Tool Invocations**: Execute tools directly. Do NOT output example ````json { ... }```` blocks in conversational text when you intend to perform an action—invoke the tool directly.",
            "4. **Run Commands Safely**: Use `bash_executor` to execute tests, builds, linting, or scripts. Avoid destructive commands unless explicitly asked.",
            "5. **Enterprise Institutional Memory (RAG)**: If an enterprise RAG tool (`query_knowledge_base`) is available and you encounter questions regarding internal infrastructure, deploy pipelines, architectures, or company standards, query the knowledge base to retrieve established organizational context.",
            "6. **Conciseness & Actionability**: Be concise, actionable, and focus on delivering accurate results.",
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
