"""The connector contract.

A connector is anything that can read a source and yield `Document` rows in the
shared schema. That's the entire extension surface: implement `fetch()`, give it
a `source` name, register it. The rest of team-brain works unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from team_brain.schema import Document

__all__ = ["Connector", "Document"]


@runtime_checkable
class Connector(Protocol):
    """Reads one source, emits Documents. `source` must match Document.source."""

    source: str

    def fetch(self) -> Iterable[Document]:
        """Yield every current Document for this source (a full snapshot).

        Ingestion upserts each and tombstones anything previously seen for this
        source that is now absent, so `fetch` should reflect the current truth.
        """
        ...
