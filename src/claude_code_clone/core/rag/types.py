"""Types and Pydantic models for Enterprise RAG."""

from typing import Any
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Raw document before chunking."""
    content: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A semantic chunk ready for embedding and indexing."""
    id: str
    content: str
    source: str
    start_line: int | None = None
    end_line: int | None = None
    vector: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Result returned from RAG retrieval."""
    id: str
    content: str
    source: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
