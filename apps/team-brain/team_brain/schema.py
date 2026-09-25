"""The ingestion contract.

Every connector, regardless of source, emits `Document` rows in this exact
shape. That single shared schema is what lets the rest of the stack (embedding,
retrieval, permissions, the agent) work unchanged no matter how many sources
are added: the core "meet data where it lives" idea.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

VISIBILITY_PUBLIC = "public"
VISIBILITY_RESTRICTED = "restricted"
_VALID_VISIBILITY = frozenset({VISIBILITY_PUBLIC, VISIBILITY_RESTRICTED})


@dataclass
class Document:
    """One unit of knowledge from any source.

    Attributes:
        source: connector name, e.g. "slack" | "github" | "markdown".
        external_id: stable id WITHIN the source. `(source, external_id)` is the
            upsert key — re-ingesting the same logical item updates in place.
        title: short human title (thread question, issue title, H1, ...).
        body: full text used for keyword search and citation display.
        created_at: source timestamp (timezone-aware, UTC).
        url: link back to the source item.
        author: who wrote/owns it (powers `who_knows`).
        project: scope bundle; queries can be bounded to one project.
        visibility: "public" (everyone) or "restricted" (only `acl` members).
        acl: member ids allowed to see a restricted doc. Empty + restricted
            means visible to no one (fail-closed).
        domains: the knowledge DOMAINS this content belongs to, applied as a
            label at ingestion (e.g. ["ops"], ["ops", "marketing"]). Empty =
            company-wide (not domain-restricted). This is the group-based access
            layer: a caller sees a domain-labeled doc only if their groups grant
            one of these domains (leadership is granted all). The label is inert
            on its own; it is ENFORCED at retrieval. See team_brain/access.py.
        metadata: free-form extras (e.g. {"kind": "code", "channel": "#eng"}).
    """

    source: str
    external_id: str
    title: str
    body: str
    created_at: datetime
    url: str = ""
    author: str = ""
    project: str = "default"
    visibility: str = VISIBILITY_PUBLIC
    acl: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("Document.source is required")
        if not self.external_id:
            raise ValueError("Document.external_id is required")
        if self.visibility not in _VALID_VISIBILITY:
            raise ValueError(
                f"Document.visibility must be one of {sorted(_VALID_VISIBILITY)}, "
                f"got {self.visibility!r}"
            )
        if self.created_at.tzinfo is None:
            raise ValueError("Document.created_at must be timezone-aware (UTC)")

    def content_hash(self) -> str:
        """Stable 16-char content fingerprint for change detection."""
        payload = f"{self.title}\n{self.body}".encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def fail_closed(self) -> bool:
        """A restricted doc with an empty ACL is visible to no one."""
        return self.visibility == VISIBILITY_RESTRICTED and not self.acl
