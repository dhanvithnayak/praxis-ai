"""OpenAI Cloud Embeddings Provider."""

import litellm

from claude_code_clone.core.rag.embeddings.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Cloud embedding provider using OpenAI text-embedding-3-small or compatible endpoints."""

    def __init__(
        self, model_name: str = "text-embedding-3-small", api_key: str | None = None
    ):
        self.model_name = model_name
        self.api_key = api_key
        self._dimension = 1536

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await litellm.aembedding(
            model=self.model_name,
            input=texts,
            api_key=self.api_key,
        )
        return [item["embedding"] for item in response.data]

    async def embed_query(self, query: str) -> list[float]:
        results = await self.embed_documents([query])
        return results[0]

    @property
    def dimension(self) -> int:
        return self._dimension
