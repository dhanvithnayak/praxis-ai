"""Document and Code Ingestion Pipeline."""

import os
from pathlib import Path
from typing import Any
from claude_code_clone.core.rag.chunking.base import BaseChunker
from claude_code_clone.core.rag.chunking.code_chunker import CodeChunker
from claude_code_clone.core.rag.chunking.markdown_chunker import MarkdownChunker
from claude_code_clone.core.rag.embeddings.base import BaseEmbeddingProvider
from claude_code_clone.core.rag.types import Chunk, Document
from claude_code_clone.core.rag.vector_store.base import BaseVectorStore
from claude_code_clone.core.tools.file_system import IGNORE_PATTERNS


class IngestionPipeline:
    """Orchestrates loading files, chunking, generating embeddings, and storing records in LanceDB."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_provider: BaseEmbeddingProvider,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.md_chunker = MarkdownChunker()
        self.code_chunker = CodeChunker()

    def _select_chunker(self, file_path: Path) -> BaseChunker:
        suffix = file_path.suffix.lower()
        if suffix in (".md", ".markdown", ".mdown", ".txt"):
            return self.md_chunker
        return self.code_chunker

    async def ingest_file(
        self,
        file_path: Path,
        collection: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Chunks, embeds, and stores a single file."""
        if not file_path.is_file():
            return 0

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return 0  # Skip binary files

        doc = Document(
            content=content,
            source=str(file_path),
            metadata=metadata or {"filename": file_path.name, "suffix": file_path.suffix},
        )

        chunker = self._select_chunker(file_path)
        chunks = chunker.chunk(doc)
        if not chunks:
            return 0

        # Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_provider.embed_documents(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.vector = emb

        return await self.vector_store.add_chunks(chunks, collection=collection)

    async def ingest_directory(
        self,
        dir_path: Path,
        collection: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Walks a directory and ingests all valid code/doc files."""
        total_chunks = 0
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS and not d.startswith(".")]
            for f in files:
                if f in IGNORE_PATTERNS or f.startswith("."):
                    continue
                file_path = Path(root) / f
                chunks_added = await self.ingest_file(
                    file_path,
                    collection=collection,
                    metadata=metadata,
                )
                total_chunks += chunks_added

        return total_chunks
