"""Lightweight workspace Repo Map generator."""

import os
from pathlib import Path
from claude_code_clone.core.tools.file_system import IGNORE_PATTERNS


class RepoMapGenerator:
    """Generates a concise architectural map of the workspace directory."""

    @classmethod
    def generate_summary(cls, workspace_dir: Path, max_files: int = 40) -> str:
        tree_lines: list[str] = []
        file_count = 0

        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in sorted(dirs) if d not in IGNORE_PATTERNS and not d.startswith(".")]
            rel_dir = Path(root).relative_to(workspace_dir)
            prefix = "" if str(rel_dir) == "." else f"{rel_dir}/"

            for f in sorted(files):
                if f in IGNORE_PATTERNS or f.startswith("."):
                    continue
                if file_count >= max_files:
                    tree_lines.append("... [remaining files omitted for brevity] ...")
                    return "\n".join(tree_lines)

                tree_lines.append(f"- {prefix}{f}")
                file_count += 1

        return "\n".join(tree_lines) if tree_lines else "Empty workspace."
