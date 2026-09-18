"""GitHub connector runs against recorded API responses (respx) — plus opt-in live.

Unchanged by the Oracle port — this connector has no database dependency.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from team_brain.access import Identity
from team_brain.connectors import CONNECTOR_BUILDERS
from team_brain.connectors.github import GitHubConnector
from team_brain.db import DocumentDB
from team_brain.ingest import ingest
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "github_repo.json").read_text())
REPO = "acme/widgets"
API = "https://api.github.com"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _mount(router: respx.Router) -> None:
    router.get(f"{API}/repos/{REPO}").mock(return_value=httpx.Response(200, json=FIXTURE["repo"]))
    router.get(f"{API}/repos/{REPO}/readme").mock(
        return_value=httpx.Response(
            200,
            json={"content": _b64(FIXTURE["readme_text"]), "html_url": FIXTURE["readme_html_url"]},
        )
    )
    router.get(url__regex=rf"{API}/repos/{REPO}/issues.*").mock(
        return_value=httpx.Response(200, json=FIXTURE["issues"])
    )
    router.get(url__regex=rf"{API}/repos/{REPO}/git/trees/.*").mock(
        return_value=httpx.Response(200, json={"tree": FIXTURE["tree"]})
    )
    for path, blob in FIXTURE["files"].items():
        router.get(url__regex=rf"{API}/repos/{REPO}/contents/{path}.*").mock(
            return_value=httpx.Response(
                200, json={"content": _b64(blob["text"]), "html_url": blob["html_url"]}
            )
        )


def test_github_connector_emits_expected_documents() -> None:
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        docs = list(GitHubConnector(REPO).fetch())

    by_id = {d.external_id: d for d in docs}
    # README
    assert by_id["readme"].metadata["kind"] == "doc"
    assert "banker's rounding" in by_id["readme"].body
    # issue + PR distinguished
    assert by_id["issue:1"].author == "alice"
    assert by_id["issue:1"].metadata["kind"] == "issue"
    assert by_id["pr:2"].metadata["kind"] == "pr"
    # code chunked, only the .py file (README.md/.txt filtered out)
    code = [d for d in docs if d.metadata.get("kind") == "code"]
    assert code, "expected code chunks"
    assert all(d.metadata["path"] == "src/money.py" for d in code)
    assert any("round_half_even" in d.body for d in code)
    # all documents satisfy the contract basics
    assert all(d.created_at.tzinfo is not None for d in docs)


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_github_failed_fetch_raises(status: int) -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{API}/repos/{REPO}").mock(
            return_value=httpx.Response(status, headers={"X-RateLimit-Remaining": "0"}, json={})
        )
        with pytest.raises(httpx.HTTPStatusError):
            list(GitHubConnector(REPO).fetch())


@pytest.mark.parametrize("acl", [[], ["alice"]])
def test_private_repo_requires_acl_at_database_read(
    db: DocumentDB, monkeypatch: pytest.MonkeyPatch, acl: list[str], tokens: dict[str, str]
) -> None:
    # Even explicitly requesting public visibility cannot expose a private repo.
    monkeypatch.setitem(CONNECTOR_BUILDERS, "github", lambda args: GitHubConnector(REPO, acl=acl))
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        router.get(f"{API}/repos/{REPO}").mock(
            return_value=httpx.Response(200, json={**FIXTURE["repo"], "private": True})
        )
        result = ingest("github", [REPO], db=db)
    assert result.upserted > 0
    assert result.skipped_fail_closed == (result.upserted if not acl else 0)
    for identity in (Identity.anonymous(), Identity.user("bob"), Identity.principal("brian")):
        db.set_identity(identity)
        assert db.get_document("github::readme") is None
    db.set_identity(Identity.user("alice"))
    assert (db.get_document("github::readme") is not None) == bool(acl)


def test_public_repo_becoming_private_revokes_old_public_rows(db: DocumentDB) -> None:
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        ingest("github", [REPO], db=db)
        db.set_identity(Identity.anonymous())
        assert db.get_document("github::readme") is not None
        router.get(f"{API}/repos/{REPO}").mock(
            return_value=httpx.Response(200, json={**FIXTURE["repo"], "private": True})
        )
        ingest("github", [REPO], db=db)
    db.set_identity(Identity.anonymous())
    assert db.get_document("github::readme") is None


@pytest.mark.parametrize("path", ["", "/issues", "/contents/src/money.py"])
def test_incomplete_sync_preserves_previous_snapshot(db: DocumentDB, path: str) -> None:
    db.upsert_document(
        Document("github", "existing", "Saved", "saved knowledge", datetime.now(UTC))
    )
    db.commit()
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        route = (
            router.get(url__regex=rf"{API}/repos/{REPO}{path}.*")
            if path
            else router.get(f"{API}/repos/{REPO}")
        )
        route.mock(
            return_value=httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, json={})
        )
        with pytest.raises(httpx.HTTPStatusError):
            ingest("github", [REPO], db=db)
    db.set_identity(Identity.anonymous())
    assert db.get_document("github::existing") is not None
    assert db.get_document("github::readme") is None  # no partial replacement
    cur = db.connection.cursor()
    cur.execute("SELECT upserted, tombstoned, error FROM ingestion_runs ORDER BY id DESC")
    upserted, tombstoned, error = cur.fetchone()
    assert (upserted, tombstoned) == (0, 0)
    assert error


def test_absent_readme_is_a_valid_snapshot(db: DocumentDB) -> None:
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        ingest("github", [REPO], db=db)
        router.get(f"{API}/repos/{REPO}/readme").mock(return_value=httpx.Response(404))
        result = ingest("github", [REPO], db=db)
    assert result.tombstoned == 1
    db.set_identity(Identity.anonymous())
    assert db.get_document("github::readme") is None
    assert db.get_document("github::issue:1") is not None


@pytest.mark.parametrize("private", [None, "false"])
def test_unknown_repository_visibility_aborts(private: object) -> None:
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        router.get(f"{API}/repos/{REPO}").mock(
            return_value=httpx.Response(200, json={**FIXTURE["repo"], "private": private})
        )
        with pytest.raises(ValueError, match="visibility"):
            list(GitHubConnector(REPO).fetch())


def test_truncated_tree_aborts() -> None:
    with respx.mock(assert_all_called=False) as router:
        _mount(router)
        router.get(url__regex=rf"{API}/repos/{REPO}/git/trees/.*").mock(
            return_value=httpx.Response(200, json={"tree": FIXTURE["tree"], "truncated": True})
        )
        with pytest.raises(ValueError, match="truncated"):
            list(GitHubConnector(REPO).fetch())


def test_repo_must_be_owner_slash_name() -> None:
    with pytest.raises(ValueError):
        GitHubConnector("noslash")


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("TEAMBRAIN_LIVE"), reason="live: set TEAMBRAIN_LIVE=1")
def test_github_live_smoke() -> None:
    docs = list(GitHubConnector("coleam00/helpline").fetch())
    assert len(docs) > 5
    assert any(d.metadata.get("kind") == "code" for d in docs)
