"""Tests for vector store operations and the RAG chain prompt."""

from pathlib import Path

import pytest
from langchain_core.documents import Document

from src.retrieval.chain import QueryResult, _format_context, build_chain
from src.retrieval.vectorstore import ingest, reset, search


# ── Vector store tests ────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate_chroma(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point ChromaDB at a temp directory and reset singleton between tests."""
    monkeypatch.setattr("src.retrieval.vectorstore.settings.chroma_persist_dir", str(tmp_path))
    monkeypatch.setattr("src.retrieval.vectorstore.settings.chroma_collection", "test")
    import src.retrieval.vectorstore as vs

    vs._store = None


def _make_docs(n: int = 3) -> list[Document]:
    return [
        Document(
            page_content=f"Pod crashed due to reason {i}. Resolution was action {i}.",
            metadata={"source": f"inc-{i:03d}.md", "severity": "SEV-1"},
        )
        for i in range(n)
    ]


def test_ingest_and_search() -> None:
    docs = _make_docs(3)
    count = ingest(docs)
    assert count == 3
    results = search("pod crash", k=2)
    assert len(results) <= 2
    assert all(isinstance(d, Document) for d in results)


def test_search_empty_store() -> None:
    results = search("anything", k=5)
    assert results == []


def test_reset_clears_data() -> None:
    ingest(_make_docs(2))
    reset()
    results = search("pod crash", k=5)
    assert results == []


# ── Chain / prompt tests ──────────────────────────────────────────────
def test_format_context_includes_source() -> None:
    docs = _make_docs(2)
    ctx = _format_context(docs)
    assert "source=inc-000.md" in ctx
    assert "source=inc-001.md" in ctx
    assert "severity=SEV-1" in ctx


def test_build_chain_has_system_and_human() -> None:
    prompt = build_chain()
    messages = prompt.messages
    assert len(messages) == 2


def test_query_returns_no_results_message() -> None:
    """When the vector store is empty, query should return a helpful message."""
    from src.retrieval.chain import query

    result = query("nonexistent problem")
    assert isinstance(result, QueryResult)
    assert "No relevant incidents" in result.answer
