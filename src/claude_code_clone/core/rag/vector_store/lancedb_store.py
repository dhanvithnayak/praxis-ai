"""LanceDB embedded vector store implementation using native Arrow / Python lists."""

import asyncio
import json
from pathlib import Path

import lancedb

from claude_code_clone.core.config.constants import LOCAL_RAG_DIR
from claude_code_clone.core.rag.types import Chunk, SearchResult
from claude_code_clone.core.rag.vector_store.base import BaseVectorStore


class LanceDBStore(BaseVectorStore):
    """Embedded, disk-backed vector database using LanceDB."""

    def __init__(self, storage_path: Path | str | None = None):
        self.storage_path = Path(storage_path) if storage_path else LOCAL_RAG_DIR
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.storage_path))

    def _sanitize_table_name(self, name: str) -> str:
        """Sanitizes collection names for LanceDB."""
        return name.replace("-", "_").replace(".", "_")

    def _get_table_names(self) -> list[str]:
        try:
            if hasattr(self.db, "list_tables"):
                res = self.db.list_tables()
                if hasattr(res, "tables"):
                    return list(res.tables)
                elif isinstance(res, list):
                    return res
            return list(self.db.table_names())
        except Exception:
            return []

    async def add_chunks(self, chunks: list[Chunk], collection: str) -> int:
        if not chunks:
            return 0

        table_name = self._sanitize_table_name(collection)

        records = [
            {
                "id": chunk.id,
                "content": chunk.content,
                "source": chunk.source,
                "start_line": chunk.start_line or 0,
                "end_line": chunk.end_line or 0,
                "vector": chunk.vector,
                "metadata": json.dumps(chunk.metadata),
            }
            for chunk in chunks
            if chunk.vector is not None
        ]

        if not records:
            return 0

        loop = asyncio.get_running_loop()

        def _sync_add():
            existing_tables = self._get_table_names()
            if table_name in existing_tables:
                tbl = self.db.open_table(table_name)
                tbl.add(records)
            else:
                self.db.create_table(table_name, data=records)

        await loop.run_in_executor(None, _sync_add)
        return len(records)

    async def search_vector(
        self,
        query_vector: list[float],
        collection: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        table_name = self._sanitize_table_name(collection)
        if table_name not in self._get_table_names():
            return []

        loop = asyncio.get_running_loop()

        def _sync_search() -> list[SearchResult]:
            tbl = self.db.open_table(table_name)
            # Use native to_list() to avoid any pandas dependency
            rows = tbl.search(query_vector).limit(top_k).to_list()
            results: list[SearchResult] = []
            for row in rows:
                try:
                    meta = json.loads(row.get("metadata", "{}"))
                except Exception:
                    meta = {}
                score = float(row.get("_distance", 0.0))
                # Convert distance to similarity score
                sim_score = 1.0 / (1.0 + score)
                results.append(
                    SearchResult(
                        id=str(row["id"]),
                        content=str(row["content"]),
                        source=str(row["source"]),
                        score=sim_score,
                        metadata=meta,
                    )
                )
            return results

        return await loop.run_in_executor(None, _sync_search)

    async def get_all_chunks(self, collection: str) -> list[Chunk]:
        table_name = self._sanitize_table_name(collection)
        if table_name not in self._get_table_names():
            return []

        loop = asyncio.get_running_loop()

        def _sync_get_all() -> list[Chunk]:
            tbl = self.db.open_table(table_name)
            arrow_table = tbl.to_arrow()
            pydict_list = arrow_table.to_pylist()
            chunks: list[Chunk] = []
            for row in pydict_list:
                try:
                    meta = json.loads(row.get("metadata", "{}"))
                except Exception:
                    meta = {}
                chunks.append(
                    Chunk(
                        id=str(row["id"]),
                        content=str(row["content"]),
                        source=str(row["source"]),
                        start_line=int(row.get("start_line", 0)),
                        end_line=int(row.get("end_line", 0)),
                        metadata=meta,
                    )
                )
            return chunks

        return await loop.run_in_executor(None, _sync_get_all)
