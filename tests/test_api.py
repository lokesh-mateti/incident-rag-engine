"""Tests for the FastAPI application."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_query_validation_rejects_short_question() -> None:
    resp = client.post("/query", json={"question": "ab"})
    assert resp.status_code == 422


def test_query_validation_rejects_bad_k() -> None:
    resp = client.post("/query", json={"question": "pod crash", "k": 0})
    assert resp.status_code == 422


def test_ingest_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ingest against a temp data dir to avoid needing real incident files."""
    (tmp_path / "inc-e2e.md").write_text(
        "id: INC-E2E\nseverity: SEV-2\nservice: test\n\n# Test\n\nBody text.\n"
    )
    monkeypatch.setattr("src.ingestion.loader.settings.incident_data_dir", str(tmp_path))
    monkeypatch.setattr(
        "src.retrieval.vectorstore.settings.chroma_persist_dir",
        str(tmp_path / "chroma"),
    )
    monkeypatch.setattr("src.retrieval.vectorstore.settings.chroma_collection", "test_api")
    import src.retrieval.vectorstore as vs
    vs._store = None

    resp = client.post("/ingest")
    assert resp.status_code == 200
    assert resp.json()["chunks_ingested"] >= 1
