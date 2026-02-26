"""Abstract Vector Store interface."""

from abc import ABC, abstractmethod

from praxis_ai.core.rag.types import Chunk, SearchResult


class BaseVectorStore(ABC):
    """Abstract interface for local or remote vector databases."""

    @abstractmethod
    async def add_chunks(self, chunks: list[Chunk], collection: str) -> int:
        """Stores chunk records with their embedding vectors."""
        ...

    @abstractmethod
    async def search_vector(
        self,
        query_vector: list[float],
        collection: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Performs vector similarity search."""
        ...

    @abstractmethod
    async def get_all_chunks(self, collection: str) -> list[Chunk]:
        """Retrieves all indexed chunks for a collection (used for BM25 hybrid search)."""
        ...
