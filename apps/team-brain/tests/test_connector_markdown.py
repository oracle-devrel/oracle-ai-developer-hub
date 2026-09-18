"""Markdown connector actually walks a folder and emits valid Documents.

Unchanged by the Oracle port — this connector has no database dependency.
"""

from __future__ import annotations

from pathlib import Path

from team_brain.connectors.markdown_docs import MarkdownDocsConnector
from team_brain.schema import Document


def test_emits_one_document_per_file(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Alpha\n\nbody a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("no heading here", encoding="utf-8")

    docs = list(MarkdownDocsConnector(str(tmp_path)).fetch())
    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)

    by_id = {d.external_id: d for d in docs}
    assert by_id["a.md"].title == "Alpha"  # H1
    assert by_id["sub/b.md"].title == "b"  # filename fallback, posix relpath
    assert all(d.created_at.tzinfo is not None for d in docs)
    assert all(d.visibility == "public" for d in docs)


def test_missing_root_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        list(MarkdownDocsConnector(str(tmp_path / "nope")).fetch())
