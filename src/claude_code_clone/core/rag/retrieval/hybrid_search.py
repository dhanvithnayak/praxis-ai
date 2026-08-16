"""Hybrid Search combining Dense Vector Search and BM25 Sparse Keyword Matching."""

from collections import defaultdict
from rank_bm25 import BM25Okapi
from claude_code_clone.core.rag.embeddings.base import BaseEmbeddingProvider
from claude_code_clone.core.rag.types import SearchResult
from claude_code_clone.core.rag.vector_store.base import BaseVectorStore


class HybridSearch:
    """Combines semantic vector search with BM25 keyword matching via Reciprocal Rank Fusion."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_provider: BaseEmbeddingProvider,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> list[SearchResult]:
        """Performs hybrid retrieval."""
        # 1. Dense Vector Search
        query_vector = await self.embedding_provider.embed_query(query)
        dense_results = await self.vector_store.search_vector(
            query_vector=query_vector,
            collection=collection,
            top_k=top_k * 2,
        )

        # 2. BM25 Sparse Search
        all_chunks = await self.vector_store.get_all_chunks(collection)
        bm25_results: list[SearchResult] = []

        if all_chunks:
            # Tokenize corpus for BM25
            tokenized_corpus = [chunk.content.lower().split() for chunk in all_chunks]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)

            # Rank by BM25 score
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for idx in ranked_indices[: top_k * 2]:
                if scores[idx] > 0:
                    chunk = all_chunks[idx]
                    bm25_results.append(
                        SearchResult(
                            id=chunk.id,
                            content=chunk.content,
                            source=chunk.source,
                            score=float(scores[idx]),
                            metadata=chunk.metadata,
                        )
                    )

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: dict[str, float] = defaultdict(float)
        result_map: dict[str, SearchResult] = {}

        # Dense rank contributions
        for rank, res in enumerate(dense_results, start=1):
            rrf_scores[res.id] += vector_weight * (1.0 / (self.rrf_k + rank))
            result_map[res.id] = res

        # BM25 rank contributions
        for rank, res in enumerate(bm25_results, start=1):
            rrf_scores[res.id] += bm25_weight * (1.0 / (self.rrf_k + rank))
            if res.id not in result_map:
                result_map[res.id] = res

        # Sort by fused score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        final_results: list[SearchResult] = []
        for chunk_id in sorted_ids[:top_k]:
            res = result_map[chunk_id]
            res.score = rrf_scores[chunk_id]
            final_results.append(res)

        return final_results
