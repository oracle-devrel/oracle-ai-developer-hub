"""Seed the larger Acme Ledger knowledge base (data/seed_full/).

A 40-person company: 24 markdown docs across ops, sales, finance, and marketing
(labelled per subfolder) plus 34 Slack threads in 8 channels, with seven
principals in data/seed_full/access.yaml. Leaves data/seed/ untouched.

Steps: init the schema, seed access, ingest every doc with its domain label in
ONE connector run, ingest the Slack export, print stats. The markdown tree is
ingested through a single connector (`_DomainMappedMarkdown`) rather than one
CLI call per subfolder because `ingest()` tombstones every row of a source that
a call did not emit, so per-subfolder calls would tombstone each other's docs.

`--report-only` prints the plan without writing anything.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SEED_FULL_DIR = REPO_DIR / "data" / "seed_full"
DOCS_DIR = SEED_FULL_DIR / "docs"
ACCESS_YAML = SEED_FULL_DIR / "access.yaml"
SLACK_EXPORT = SEED_FULL_DIR / "slack_export.json"

# Subfolder -> domains applied to every doc under it. Empty list = company-wide.
DOMAIN_MAP: dict[str, list[str]] = {
    "engineering": [],
    "people": [],
    "ops": ["ops"],
    "marketing": ["marketing"],
    "sales": ["sales"],
    "finance": ["finance"],
}


def _build_domain_mapped_markdown_connector():
    """Build the custom multi-domain markdown connector (see module docstring)."""
    import re

    from team_brain.schema import Document

    h1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)

    class _DomainMappedMarkdown:
        source = "markdown"

        def __init__(self, root: Path, domain_map: dict[str, list[str]]) -> None:
            self.root = root
            self.domain_map = domain_map

        def fetch(self) -> Iterable[Document]:
            if not self.root.exists():
                raise FileNotFoundError(f"markdown root not found: {self.root}")
            for subfolder, domains in sorted(self.domain_map.items()):
                folder = self.root / subfolder
                if not folder.exists():
                    continue
                for path in sorted(folder.rglob("*.md")):
                    text = path.read_text(encoding="utf-8")
                    rel = path.relative_to(self.root).as_posix()  # e.g. "ops/oncall-rotation.md"
                    m = h1.search(text)
                    title = m.group(1).strip() if m else path.stem
                    created = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
                    yield Document(
                        source=self.source,
                        external_id=rel,
                        title=title,
                        body=text,
                        url=f"file://{path.resolve().as_posix()}",
                        created_at=created,
                        project="default",
                        domains=list(domains),
                        metadata={"path": rel, "domain_folder": subfolder},
                    )

    return _DomainMappedMarkdown(DOCS_DIR, DOMAIN_MAP)


def _register_full_markdown_connector() -> None:
    """Runtime-register our connector under the SAME 'markdown' key.

    Uses team_brain.connectors.register(), the library's own public
    extension point (its own docstring: "write a module ... then register a
    builder here" — calling register() from outside is the same operation,
    just not committed into that file). This overwrites the in-process
    dict entry only; no file under team_brain/ is touched.
    """
    from team_brain.connectors import register

    connector = _build_domain_mapped_markdown_connector()
    register("markdown", lambda args: connector)


def seed_access() -> None:
    from team_brain.access import AccessControl, load_access_spec
    from team_brain.access import seed_access as do_seed
    from team_brain.db import DocumentDB

    db = DocumentDB()
    try:
        db.init_schema()
    finally:
        db.close()

    ac = AccessControl()
    try:
        tokens = do_seed(ac, load_access_spec(str(ACCESS_YAML)))
        principals = ac.list_principals()
    finally:
        ac.close()

    print(f"Seeded {len(principals)} principals from {ACCESS_YAML}:")
    for p in principals:
        print(f"  {p.describe()}")
    print("\nTokens:")
    for user, token in tokens.items():
        print(f"  {user:8} {token}")
    print()


def ingest_docs() -> None:
    from team_brain.ingest import ingest

    _register_full_markdown_connector()
    res = ingest("markdown", [])
    print(
        f"[markdown] upserted={res.upserted} tombstoned={res.tombstoned} "
        f"fail_closed={res.skipped_fail_closed}"
    )


def ingest_slack() -> None:
    from team_brain.ingest import ingest

    res = ingest("slack", ["--export", str(SLACK_EXPORT)])
    print(
        f"[slack] upserted={res.upserted} tombstoned={res.tombstoned} "
        f"fail_closed={res.skipped_fail_closed}"
    )


def print_stats() -> None:
    from team_brain.db import DocumentDB

    db = DocumentDB()
    try:
        db.init_schema()
        import json as _json

        print(_json.dumps(db.stats(), indent=2))
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-access", action="store_true", help="skip the access-control seed step"
    )
    args = parser.parse_args()

    if not args.skip_access:
        seed_access()
    ingest_docs()
    ingest_slack()
    print_stats()
    return 0


if __name__ == "__main__":
    sys.exit(main())
