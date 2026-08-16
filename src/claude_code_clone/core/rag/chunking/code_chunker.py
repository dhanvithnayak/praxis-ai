"""Code and structured configuration chunker."""

import uuid

from claude_code_clone.core.rag.chunking.base import BaseChunker
from claude_code_clone.core.rag.types import Chunk, Document


class CodeChunker(BaseChunker):
    """Chunks codebases and infra configurations (Terraform, YAML, Python, TS) using sliding windows."""

    def __init__(self, max_lines: int = 50, overlap_lines: int = 10):
        self.max_lines = max_lines
        self.overlap_lines = overlap_lines

    def chunk(self, document: Document) -> list[Chunk]:
        lines = document.content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return []

        chunks: list[Chunk] = []
        step = max(1, self.max_lines - self.overlap_lines)

        for start_idx in range(0, total_lines, step):
            end_idx = min(start_idx + self.max_lines, total_lines)
            chunk_lines = lines[start_idx:end_idx]
            chunk_text = "\n".join(chunk_lines).strip()

            if not chunk_text:
                continue

            chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    source=document.source,
                    start_line=start_idx + 1,
                    end_line=end_idx,
                    metadata={**document.metadata, "type": "code"},
                )
            )

            if end_idx >= total_lines:
                break

        return chunks
