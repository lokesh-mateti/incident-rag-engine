"""ChromaDB vector store backed by local HuggingFace embeddings."""

from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import settings

_store: Chroma | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
    )


def get_vectorstore() -> Chroma:
    """Return (and lazily create) the singleton Chroma instance."""
    global _store  # noqa: PLW0603
    if _store is None:
        _store = Chroma(
            collection_name=settings.chroma_collection,
            embedding_function=_get_embeddings(),
            persist_directory=str(settings.chroma_path),
        )
    return _store


def ingest(docs: list[Document]) -> int:
    """Add documents to the vector store.  Returns count of chunks added."""
    store = get_vectorstore()
    store.add_documents(docs)
    return len(docs)


def search(query: str, k: int = 5) -> list[Document]:
    """Similarity search returning the top-k most relevant chunks."""
    store = get_vectorstore()
    return store.similarity_search(query, k=k)


def reset() -> None:
    """Drop and recreate the collection — useful for re-ingestion."""
    global _store  # noqa: PLW0603
    store = get_vectorstore()
    store.delete_collection()
    _store = None
