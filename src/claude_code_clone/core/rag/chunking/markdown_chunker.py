"""Markdown structure-aware chunker preserving header hierarchy."""

import re
import uuid
from claude_code_clone.core.rag.chunking.base import BaseChunker
from claude_code_clone.core.rag.types import Chunk, Document


class MarkdownChunker(BaseChunker):
    """Splits Markdown by headers (#, ##, ###) to maintain contextual coherence."""

    def __init__(self, max_chunk_chars: int = 1500, min_chunk_chars: int = 100):
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars
        self.header_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

    def chunk(self, document: Document) -> list[Chunk]:
        content = document.content
        lines = content.splitlines()
        chunks: list[Chunk] = []

        sections: list[tuple[str, list[str], int]] = []
        current_header = "Introduction"
        current_lines: list[str] = []
        start_line = 1

        for line_no, line in enumerate(lines, start=1):
            match = self.header_pattern.match(line)
            if match:
                if current_lines:
                    sections.append((current_header, current_lines, start_line))
                current_header = line.strip()
                current_lines = [line]
                start_line = line_no
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_header, current_lines, start_line))

        # Build chunks from sections
        for header, sec_lines, s_line in sections:
            sec_text = "\n".join(sec_lines).strip()
            if not sec_text:
                continue

            end_line = s_line + len(sec_lines) - 1

            if len(sec_text) <= self.max_chunk_chars:
                chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=sec_text,
                        source=document.source,
                        start_line=s_line,
                        end_line=end_line,
                        metadata={**document.metadata, "header": header, "type": "markdown"},
                    )
                )
            else:
                # Sub-split large sections by paragraphs
                paragraphs = sec_text.split("\n\n")
                accumulated: list[str] = []
                current_len = 0
                sub_start = s_line

                for para in paragraphs:
                    para_len = len(para)
                    if current_len + para_len > self.max_chunk_chars and accumulated:
                        block_text = f"[{header}]\n" + "\n\n".join(accumulated)
                        chunks.append(
                            Chunk(
                                id=f"chunk_{uuid.uuid4().hex[:8]}",
                                content=block_text,
                                source=document.source,
                                start_line=sub_start,
                                end_line=s_line,
                                metadata={**document.metadata, "header": header, "type": "markdown"},
                            )
                        )
                        accumulated = [para]
                        current_len = para_len
                        sub_start = s_line
                    else:
                        accumulated.append(para)
                        current_len += para_len

                if accumulated:
                    block_text = f"[{header}]\n" + "\n\n".join(accumulated)
                    chunks.append(
                        Chunk(
                            id=f"chunk_{uuid.uuid4().hex[:8]}",
                            content=block_text,
                            source=document.source,
                            start_line=sub_start,
                            end_line=end_line,
                            metadata={**document.metadata, "header": header, "type": "markdown"},
                        )
                    )

        return chunks
