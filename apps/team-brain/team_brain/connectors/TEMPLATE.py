"""COPY ME to write your own connector.

Three steps:
  1. Rename this file (e.g. `notion.py`) and rename `MyConnector`.
  2. Set `source` to a unique name and implement `fetch()` to yield Documents
     in the shared schema (see team_brain/schema.py).
  3. Register a builder in team_brain/connectors/__init__.py, then:
        uv run team-brain ingest <your-source>

Everything else — embedding, hybrid retrieval, permissions, the agent, MCP —
works unchanged the moment your rows land in the `documents` table.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from team_brain.schema import Document


class MyConnector:
    source = "template"  # <- change me to your source name

    def fetch(self) -> Iterable[Document]:
        # Replace this stub with real reads from your system. For each item, yield:
        #
        #   yield Document(
        #       source=self.source,
        #       external_id="stable-id-within-source",   # upsert key
        #       title="short title",
        #       body="full text (used for keyword search + citation)",
        #       created_at=datetime.now(UTC),            # tz-aware!
        #       url="https://link.to/item",
        #       author="who wrote it",                   # powers who_knows
        #       # visibility="restricted", acl=["alice"] # for private content
        #   )
        raise NotImplementedError(
            "Fill in MyConnector.fetch() — see team_brain/connectors/markdown_docs.py "
            "for a minimal working example."
        )
        # Unreachable example (kept so the return type is obvious):
        yield Document("template", "example", "Example", "body", datetime.now(UTC))
