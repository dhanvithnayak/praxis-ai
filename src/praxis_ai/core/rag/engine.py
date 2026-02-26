"""High-level Enterprise RAG Engine coordinator."""

from pathlib import Path
from typing import Any

from praxis_ai.core.config.constants import DEFAULT_RAG_COLLECTION
from praxis_ai.core.config.settings import Settings
from praxis_ai.core.rag.embeddings.base import BaseEmbeddingProvider
from praxis_ai.core.rag.embeddings.fastembed_provider import FastEmbedProvider
from praxis_ai.core.rag.embeddings.openai_provider import (
    OpenAIEmbeddingProvider,
)
from praxis_ai.core.rag.ingestion.pipeline import IngestionPipeline
from praxis_ai.core.rag.retrieval.hybrid_search import HybridSearch
from praxis_ai.core.rag.types import SearchResult
from praxis_ai.core.rag.vector_store.base import BaseVectorStore
from praxis_ai.core.rag.vector_store.lancedb_store import LanceDBStore


class RAGEngine:
    """Central interface for indexing and querying enterprise organizational context."""

    def __init__(
        self,
        settings: Settings | None = None,
        vector_store: BaseVectorStore | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
    ):
        self.settings = settings or Settings.load()

        if embedding_provider:
            self.embedding_provider = embedding_provider
        elif "openai" in self.settings.rag_embedding_model.lower():
            self.embedding_provider = OpenAIEmbeddingProvider(
                model_name=self.settings.rag_embedding_model,
                api_key=self.settings.openai_api_key,
            )
        else:
            self.embedding_provider = FastEmbedProvider(
                model_name=self.settings.rag_embedding_model
            )

        self.vector_store = vector_store or LanceDBStore(
            storage_path=self.settings.rag_storage_path
        )
        self.ingestion_pipeline = IngestionPipeline(
            vector_store=self.vector_store,
            embedding_provider=self.embedding_provider,
        )
        self.retriever = HybridSearch(
            vector_store=self.vector_store,
            embedding_provider=self.embedding_provider,
        )

    async def ingest_path(
        self,
        target_path: str | Path,
        collection: str = DEFAULT_RAG_COLLECTION,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Ingests a file or directory into the vector store."""
        p = Path(target_path).resolve()
        if p.is_file():
            return await self.ingestion_pipeline.ingest_file(
                p, collection=collection, metadata=metadata
            )
        elif p.is_dir():
            return await self.ingestion_pipeline.ingest_directory(
                p, collection=collection, metadata=metadata
            )
        else:
            raise FileNotFoundError(f"Path '{target_path}' does not exist.")

    async def search(
        self,
        query: str,
        collection: str = DEFAULT_RAG_COLLECTION,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Runs hybrid search across indexed chunks in the given collection."""
        return await self.retriever.search(
            query=query, collection=collection, top_k=top_k
        )
