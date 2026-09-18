"""Shared test fixtures (Oracle AI Database edition).

Database-backed tests run against the disposable TEAMBRAIN_TEST schema in the
`team-brain-oracle` Oracle AI Database Free container (localhost:1521,
service FREEPDB1). We point ORACLE_USER at that schema BEFORE importing
team_brain so config.py picks it up, force the LLM offline for determinism
(unless TEAMBRAIN_LIVE), and truncate between tests for isolation.

Modules that need the database carry `pytestmark = pytest.mark.requires_oracle`.
When the database is unreachable those tests are skipped, after one quick
connection attempt, and the pure-Python tests (schema, connectors, enrichment,
retrieval math, LLM offline path) still run.

Identity lives in the DATABASE (see team_brain/access.py), not in Python, so
these fixtures hand out `Identity` values (or a seeded {username: token} map)
rather than the raw usernames and domain lists used by the workshop version.
"""

from __future__ import annotations

import os

# Must happen before any team_brain import so config picks these up.
os.environ["ORACLE_USER"] = "TEAMBRAIN_TEST"
os.environ.setdefault("ORACLE_PASSWORD", "TeamBrain123")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
if not os.environ.get("TEAMBRAIN_LIVE"):
    os.environ["LLM_API_KEY"] = ""
    os.environ["OPENROUTER_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""

import time  # noqa: E402
from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402

from team_brain.access import AccessControl, Identity, load_access_spec, seed_access  # noqa: E402
from team_brain.config import REPO_DIR  # noqa: E402
from team_brain.db import DocumentDB  # noqa: E402

# Set TEAMBRAIN_DB_WAIT=<seconds> to keep retrying while a fresh container boots.
_DB_WAIT_SECONDS = float(os.environ.get("TEAMBRAIN_DB_WAIT", "0"))
_db_unavailable: str | None = None


@pytest.fixture(scope="session", autouse=True)
def _ensure_schema() -> None:
    """Create the test schema objects once per session, or record why it cannot.

    DocumentDB.init_schema() creates the documents table, the Oracle Text
    index, the identity admin tables, the trusted tb_session package, and the
    row policy: everything AccessControl needs too.
    """
    global _db_unavailable
    deadline = time.monotonic() + _DB_WAIT_SECONDS
    while True:
        try:
            d = DocumentDB()
            d.init_schema()
            d.close()
            return
        except Exception as exc:  # noqa: BLE001
            if time.monotonic() >= deadline:
                _db_unavailable = f"{type(exc).__name__}: {exc}"
                return
            time.sleep(2)


@pytest.fixture(autouse=True)
def _skip_without_database(request: pytest.FixtureRequest) -> None:
    """Skip database-backed tests when TEAMBRAIN_TEST is not reachable."""
    if _db_unavailable is None:
        return
    needs_db = request.node.get_closest_marker("requires_oracle") is not None or bool(
        {"db", "tokens"} & set(request.fixturenames)
    )
    if needs_db:
        pytest.skip(
            f"Oracle AI Database not reachable at localhost:1521/FREEPDB1 ({_db_unavailable})"
        )


@pytest.fixture
def db() -> Iterator[DocumentDB]:
    """A clean DocumentDB (table truncated) with INGEST identity for one test.

    INGEST mode sees every row (no policy predicate), which is what most
    tests want by default: seed data, then read it back. Tests that assert
    the permission/domain leak matrix explicitly switch identity via
    `db.set_identity(...)` before reading.
    """
    d = DocumentDB()
    d.init_schema()
    d.set_identity(Identity.ingest())
    d.truncate()
    d.commit()
    yield d
    d.close()


@pytest.fixture
def seed_docs() -> str:
    return str(REPO_DIR / "data" / "seed" / "docs")


@pytest.fixture
def slack_export() -> str:
    return str(REPO_DIR / "data" / "seed" / "slack_export.json")


@pytest.fixture
def domain_slack_export() -> str:
    return str(REPO_DIR / "data" / "seed" / "slack_export_domains.json")


@pytest.fixture
def access_spec_path() -> str:
    return str(REPO_DIR / "data" / "seed" / "access.yaml")


@pytest.fixture
def tokens(access_spec_path: str) -> dict[str, str]:
    """Seed principals/groups/tokens into the test schema; return {username: token}."""
    ac = AccessControl()
    try:
        ac.init_schema()
        result = seed_access(ac, load_access_spec(access_spec_path))
    finally:
        ac.close()
    return result


@pytest.fixture
def alice() -> Identity:
    """Raw `user` identity (ACL-only, no domain grant), the legacy `--user` path."""
    return Identity.user("alice")


@pytest.fixture
def bob() -> Identity:
    return Identity.user("bob")
