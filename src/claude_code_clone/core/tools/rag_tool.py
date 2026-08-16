"""RAG Knowledge Base Tool for autonomous agent querying."""

from typing import Any
from pydantic import BaseModel, Field
from claude_code_clone.core.agent.types import ToolResult
from claude_code_clone.core.config.constants import DEFAULT_RAG_COLLECTION
from claude_code_clone.core.rag.engine import RAGEngine
from claude_code_clone.core.tools.base import BaseTool, ExecutionContext


class QueryKnowledgeBaseArgs(BaseModel):
    query: str = Field(description="The question or search query to look up in the enterprise knowledge base")
    collection: str = Field(
        default=DEFAULT_RAG_COLLECTION,
        description="The knowledge collection to search within (e.g. 'enterprise-docs', 'infra-playbooks', 'architecture')",
    )
    top_k: int = Field(default=4, description="Number of relevant chunks to retrieve")


class QueryKnowledgeBaseTool(BaseTool):
    name = "query_knowledge_base"
    description = (
        "Queries the enterprise RAG knowledge base for institutional memory, infrastructure configs, "
        "deployment playbooks, architecture decision records, or internal SDK documentation."
    )
    is_destructive = False
    args_schema = QueryKnowledgeBaseArgs

    def __init__(self, engine: RAGEngine | None = None):
        self._engine = engine

    def _get_engine(self) -> RAGEngine:
        if self._engine is None:
            self._engine = RAGEngine()
        return self._engine

    async def execute(self, params: dict[str, Any], context: ExecutionContext) -> ToolResult:
        try:
            args = QueryKnowledgeBaseArgs(**params)
            engine = self._get_engine()
            results = await engine.search(query=args.query, collection=args.collection, top_k=args.top_k)

            if not results:
                return ToolResult(
                    tool_call_id="",
                    tool_name=self.name,
                    output=f"No matching documents found in collection '{args.collection}' for query: '{args.query}'.",
                )

            formatted_blocks: list[str] = []
            for i, r in enumerate(results, 1):
                source_info = f"Source: {r.source}"
                if "header" in r.metadata:
                    source_info += f" | Section: {r.metadata['header']}"
                block = f"--- [Result {i}] ({source_info} | Score: {r.score:.3f}) ---\n{r.content}"
                formatted_blocks.append(block)

            full_output = (
                f"Retrieved {len(results)} relevant section(s) from enterprise knowledge base:\n\n"
                + "\n\n".join(formatted_blocks)
            )

            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=full_output,
                metadata={"count": len(results), "collection": args.collection},
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                output=f"Error querying knowledge base: {e}",
                is_error=True,
            )
