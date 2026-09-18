"""CLI subcommands via subprocess — exit codes and output.

Oracle port: identity flags are `--as <principal>` / `--user <raw>` /
`--token <T>` (the database resolves the grant); the old `--user alice` path
still exists (raw, ACL-only) but the primary demo path is `--as jeff` etc.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from team_brain.cli import main
from team_brain.config import REPO_DIR
from team_brain.db import DocumentDB

pytestmark = pytest.mark.requires_oracle


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "team_brain.cli", *args],
        env=dict(os.environ),  # ORACLE_USER points at the test schema (conftest)
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_stats_runs(db: DocumentDB) -> None:
    r = _run("stats")
    assert r.returncode == 0
    assert "live_documents" in r.stdout


def test_ingest_then_ask_then_eval(
    db: DocumentDB, seed_docs: str, slack_export: str, tokens: dict[str, str]
) -> None:
    r1 = _run("ingest", "markdown", seed_docs)
    assert r1.returncode == 0
    assert "[markdown]" in r1.stdout

    r2 = _run("ingest", "slack", "--export", slack_export)
    assert r2.returncode == 0

    r3 = _run("ask", "how do we deploy billing?", "--as", "jeff")
    assert r3.returncode == 0
    assert r3.stdout.strip()

    r4 = _run("eval")
    assert r4.returncode == 0
    assert "recall@" in r4.stdout


def test_whoami_as_principal(db: DocumentDB, tokens: dict[str, str]) -> None:
    r = _run("whoami", "--as", "brian")
    assert r.returncode == 0
    assert "brian" in r.stdout.lower()


def test_ask_with_bad_token_is_denied(db: DocumentDB, tokens: dict[str, str]) -> None:
    r = _run("ask", "anything", "--token", "tb_not_a_real_token")
    assert r.returncode == 1
    assert "denied" in (r.stdout + r.stderr).lower()


def test_template_ingest_fails_friendly(db: DocumentDB) -> None:
    r = _run("ingest", "template")
    assert r.returncode != 0
    assert "error:" in r.stderr.lower()
    assert "traceback" not in r.stderr.lower()  # friendly, not a stack dump


# --- in-process (measured by coverage) -------------------------------------


def test_main_stats_inprocess(db: DocumentDB, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["team-brain", "stats"])
    assert main() == 0


def test_main_ingest_ask_eval_inprocess(
    db: DocumentDB, monkeypatch: pytest.MonkeyPatch, seed_docs: str, slack_export: str
) -> None:
    monkeypatch.setattr(sys, "argv", ["team-brain", "ingest", "markdown", seed_docs])
    assert main() == 0
    monkeypatch.setattr(sys, "argv", ["team-brain", "ingest", "slack", "--export", slack_export])
    assert main() == 0
    monkeypatch.setattr(
        sys, "argv", ["team-brain", "ask", "how to deploy billing?", "--user", "alice"]
    )
    assert main() == 0
    monkeypatch.setattr(sys, "argv", ["team-brain", "eval"])
    assert main() == 0


def test_main_bad_source_returns_error(db: DocumentDB, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["team-brain", "ingest", "nonesuch"])
    assert main() == 1


def test_main_access_seed_and_principals_inprocess(
    db: DocumentDB, monkeypatch: pytest.MonkeyPatch, access_spec_path: str
) -> None:
    monkeypatch.setattr(sys, "argv", ["team-brain", "access", "seed", "--file", access_spec_path])
    assert main() == 0
    monkeypatch.setattr(sys, "argv", ["team-brain", "principals"])
    assert main() == 0


def test_main_whoami_as_and_bad_token_inprocess(
    db: DocumentDB, monkeypatch: pytest.MonkeyPatch, access_spec_path: str
) -> None:
    monkeypatch.setattr(sys, "argv", ["team-brain", "access", "seed", "--file", access_spec_path])
    assert main() == 0
    monkeypatch.setattr(sys, "argv", ["team-brain", "whoami", "--as", "jeff"])
    assert main() == 0
    monkeypatch.setattr(sys, "argv", ["team-brain", "whoami", "--token", "tb_not_a_real_token"])
    assert main() == 1
