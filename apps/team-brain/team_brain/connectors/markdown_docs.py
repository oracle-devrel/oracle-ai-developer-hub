"""Markdown docs connector — the reference implementation.

Walks a folder of `.md` files and emits one public Document per file. The
simplest possible connector: read the template stub and this side by side to
write your own.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from team_brain.schema import Document

_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


class MarkdownDocsConnector:
    source = "markdown"

    def __init__(
        self, root: str, project: str = "default", domains: list[str] | None = None
    ) -> None:
        self.root = Path(root)
        self.project = project
        self.domains = domains or []

    def fetch(self) -> Iterable[Document]:
        if not self.root.exists():
            raise FileNotFoundError(f"markdown root not found: {self.root}")
        for path in sorted(self.root.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(self.root).as_posix()
            m = _H1.search(text)
            title = m.group(1).strip() if m else path.stem
            created = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            yield Document(
                source=self.source,
                external_id=rel,
                title=title,
                body=text,
                url=f"file://{path.resolve().as_posix()}",
                created_at=created,
                project=self.project,
                domains=list(self.domains),
                metadata={"path": rel},
            )
