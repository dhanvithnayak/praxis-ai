"""Local CPU ONNX embeddings using FastEmbed (zero external API keys needed)."""

import asyncio
from fastembed import TextEmbedding
from claude_code_clone.core.config.constants import DEFAULT_EMBEDDING_MODEL
from claude_code_clone.core.rag.embeddings.base import BaseEmbeddingProvider


class FastEmbedProvider(BaseEmbeddingProvider):
    """Local, high-speed embedding model powered by FastEmbed & ONNX Runtime."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self._model: TextEmbedding | None = None
        self._dimension = 384  # Default for BAAI/bge-small-en-v1.5

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        # Run in thread pool to avoid blocking async event loop
        embeddings = await loop.run_in_executor(
            None,
            lambda: list(self._get_model().embed(texts)),
        )
        return [emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings]

    async def embed_query(self, query: str) -> list[float]:
        results = await self.embed_documents([query])
        return results[0]

    @property
    def dimension(self) -> int:
        return self._dimension
