"""FastAPI application exposing ingest and query endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.ingestion.chunker import chunk_documents
from src.ingestion.loader import load_incidents
from src.retrieval import chain
from src.retrieval.vectorstore import ingest, reset

app = FastAPI(
    title="Incident RAG Engine",
    version="0.1.0",
    description="RAG-powered incident resolution for Cloud/K8s operations",
)


# ── Schemas ───────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, examples=["pod CrashLoopBackOff in prod"])
    k: int = Field(5, ge=1, le=20)


class SourceDoc(BaseModel):
    source: str
    severity: str | None = None
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceDoc]


class IngestResponse(BaseModel):
    chunks_ingested: int


# ── Routes ────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest_incidents(force: bool = False) -> IngestResponse:
    """Load incident markdown files, chunk, and upsert into ChromaDB.
    Pass ?force=true to drop and rebuild the collection first."""
    if force:
        reset()
    docs = load_incidents()
    chunks = chunk_documents(docs)
    n = ingest(chunks)
    return IngestResponse(chunks_ingested=n)


@app.post("/query", response_model=QueryResponse)
def query_incidents(req: QueryRequest) -> QueryResponse:
    result = chain.query(req.question, k=req.k)
    sources = [
        SourceDoc(
            source=d.metadata.get("source", "unknown"),
            severity=d.metadata.get("severity"),
            excerpt=d.page_content[:200],
        )
        for d in result.sources
    ]
    return QueryResponse(answer=result.answer, sources=sources)
