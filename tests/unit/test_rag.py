"""Unit and integration tests for Enterprise RAG subsystem."""

from pathlib import Path
import pytest
from claude_code_clone.core.rag.chunking.code_chunker import CodeChunker
from claude_code_clone.core.rag.chunking.markdown_chunker import MarkdownChunker
from claude_code_clone.core.rag.embeddings.fastembed_provider import FastEmbedProvider
from claude_code_clone.core.rag.engine import RAGEngine
from claude_code_clone.core.rag.types import Document
from claude_code_clone.core.rag.vector_store.lancedb_store import LanceDBStore
from claude_code_clone.core.tools.base import ExecutionContext
from claude_code_clone.core.tools.rag_tool import QueryKnowledgeBaseTool


def test_markdown_chunker():
    doc_text = (
        "# Infrastructure Standards\n\n"
        "All services must run in Kubernetes clusters with Helm.\n\n"
        "## Deployment Policy\n\n"
        "Production deployments require dual-approvals and zero-downtime rolling updates.\n\n"
        "## CI/CD Pipeline\n\n"
        "GitHub Actions triggers the release tag automatically.\n"
    )
    doc = Document(content=doc_text, source="infra/standards.md")
    chunker = MarkdownChunker(max_chunk_chars=500)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 3
    headers = [c.metadata.get("header") for c in chunks]
    assert any("Infrastructure Standards" in h for h in headers if h)
    assert any("Deployment Policy" in h for h in headers if h)


def test_code_chunker():
    code_text = "\n".join(f"resource \"aws_s3_bucket\" \"b_{i}\" {{ bucket = \"corp-{i}\" }}" for i in range(30))
    doc = Document(content=code_text, source="infra/s3.tf")
    chunker = CodeChunker(max_lines=15, overlap_lines=3)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 2
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 15


@pytest.mark.asyncio
async def test_fastembed_local_embeddings():
    embedder = FastEmbedProvider()
    texts = ["Kubernetes cluster deployment", "Terraform AWS infrastructure module"]
    vectors = await embedder.embed_documents(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    query_vec = await embedder.embed_query("How to deploy k8s?")
    assert len(query_vec) == 384


@pytest.mark.asyncio
async def test_rag_engine_lifecycle(tmp_path: Path):
    # Setup test doc
    docs_dir = tmp_path / "corp_docs"
    docs_dir.mkdir()
    infra_doc = docs_dir / "kubernetes_guide.md"
    infra_doc.write_text(
        "# Enterprise Kubernetes Playbook\n\n"
        "Our standard namespace for authentication service is `corp-auth-prod`.\n"
        "Always use secret manager `vault.corp.internal` for database credentials.\n"
    )

    rag_store_path = tmp_path / "rag_data"
    engine = RAGEngine(
        vector_store=LanceDBStore(storage_path=rag_store_path),
        embedding_provider=FastEmbedProvider(),
    )

    # Ingest
    count = await engine.ingest_path(docs_dir, collection="test_infra")
    assert count > 0

    # Search
    results = await engine.search("Where is auth service secret manager configured?", collection="test_infra", top_k=2)
    assert len(results) > 0
    assert "vault.corp.internal" in results[0].content

    # Tool test
    tool = QueryKnowledgeBaseTool(engine=engine)
    context = ExecutionContext(workspace_dir=tmp_path)
    tool_res = await tool.execute(
        {"query": "auth service namespace", "collection": "test_infra"},
        context,
    )
    assert not tool_res.is_error
    assert "corp-auth-prod" in tool_res.output
