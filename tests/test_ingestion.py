"""Tests for incident document loading and chunking."""

from pathlib import Path

import pytest

from src.ingestion.chunker import chunk_documents
from src.ingestion.loader import load_incidents

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_dir(tmp_path: Path) -> Path:
    """Write two small incident files to a temp directory."""
    (tmp_path / "inc-test-001.md").write_text(
        "id: INC-TEST-001\n"
        "severity: SEV-1\n"
        "service: test-api\n"
        "\n"
        "# INC-TEST-001: Test Incident\n\n"
        "## Detection\nAlert fired.\n\n"
        "## Root Cause\nBad config pushed.\n\n"
        "## Resolution\nRolled back.\n"
    )
    (tmp_path / "inc-test-002.md").write_text(
        "id: INC-TEST-002\n"
        "severity: SEV-2\n"
        "service: auth-service\n"
        "\n"
        "# INC-TEST-002: Auth Timeout\n\n"
        "## Detection\nLatency spike.\n\n"
        "## Root Cause\nConnection pool exhausted.\n\n"
        "## Resolution\nIncreased pool size.\n"
    )
    return tmp_path


def test_load_incidents_reads_all_files(sample_dir: Path) -> None:
    docs = load_incidents(sample_dir)
    assert len(docs) == 2


def test_load_incidents_extracts_metadata(sample_dir: Path) -> None:
    docs = load_incidents(sample_dir)
    meta = docs[0].metadata
    assert meta["id"] == "INC-TEST-001"
    assert meta["severity"] == "SEV-1"
    assert meta["service"] == "test-api"
    assert meta["source"] == "inc-test-001.md"


def test_load_incidents_body_excludes_frontmatter(sample_dir: Path) -> None:
    docs = load_incidents(sample_dir)
    body = docs[0].page_content
    assert "id: INC-TEST-001" not in body
    assert "# INC-TEST-001" in body


def test_load_incidents_empty_dir(tmp_path: Path) -> None:
    docs = load_incidents(tmp_path)
    assert docs == []


def test_chunk_documents_produces_chunks(sample_dir: Path) -> None:
    docs = load_incidents(sample_dir)
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= len(docs)


def test_chunk_documents_preserves_metadata(sample_dir: Path) -> None:
    docs = load_incidents(sample_dir)
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=20)
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert "severity" in chunk.metadata


def test_real_incident_data_loads() -> None:
    """Smoke test against the actual data/incidents directory."""
    data_dir = Path(__file__).parent.parent / "data" / "incidents"
    if not data_dir.exists():
        pytest.skip("data/incidents not found")
    docs = load_incidents(data_dir)
    assert len(docs) >= 8
    for doc in docs:
        assert doc.metadata.get("id"), f"Missing id in {doc.metadata.get('source')}"
        assert doc.metadata.get("severity"), f"Missing severity in {doc.metadata.get('source')}"
