"""Base Chunker interface."""

from abc import ABC, abstractmethod

from claude_code_clone.core.rag.types import Chunk, Document


class BaseChunker(ABC):
    """Abstract chunker for turning Documents into searchable Chunks."""

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Splits a document into semantic chunks."""
        ...
