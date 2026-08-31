"""Abstract Base Embedding Provider."""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a batch of text chunks."""
        ...

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generates an embedding vector for a single search query."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension size."""
        ...
