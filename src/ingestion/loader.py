"""Load incident markdown files and extract structured metadata from frontmatter."""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document

from src.config import settings

# Matches YAML-ish key: value lines at the top of each incident file.
_META_RE = re.compile(r"^(?P<key>[A-Za-z_-]+):\s*(?P<value>.+)$")


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split leading key: value block from the body.  Not full YAML — just
    the flat metadata block used in our incident templates."""
    lines = text.splitlines(keepends=True)
    meta: dict[str, str] = {}
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            body_start = i
            break
        m = _META_RE.match(stripped)
        if m:
            meta[m.group("key").lower()] = m.group("value").strip()
            body_start = i + 1
        else:
            body_start = i
            break
    body = "".join(lines[body_start:]).strip()
    return meta, body


def load_incidents(data_dir: Path | None = None) -> list[Document]:
    """Read every .md file under *data_dir* and return LangChain Documents
    with metadata pulled from the file's frontmatter block."""
    data_dir = data_dir or settings.data_path
    docs: list[Document] = []
    for path in sorted(data_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        meta["source"] = path.name
        docs.append(Document(page_content=body, metadata=meta))
    return docs
