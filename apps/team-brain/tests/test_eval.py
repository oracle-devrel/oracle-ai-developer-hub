"""The eval gate: recall@k, no permission leak, RRF ≥ naive linear.

Unchanged by the Oracle port at the API level — `run_eval()` resolves each
golden question's identity from `user:`/`principal:`/`token:` in
data/golden_questions.yaml (see team_brain/evaluate.py `_identity_for`).
"""

from __future__ import annotations

import pytest

from team_brain.db import DocumentDB
from team_brain.evaluate import RECALL_THRESHOLD, run_eval
from team_brain.ingest import ingest

pytestmark = pytest.mark.requires_oracle


def _ingest_seed(seed_docs: str, slack_export: str) -> None:
    ingest("markdown", [seed_docs])
    ingest("slack", ["--export", slack_export])


def test_eval_passes_on_seed(db: DocumentDB, seed_docs: str, slack_export: str) -> None:
    _ingest_seed(seed_docs, slack_export)
    report = run_eval()
    assert report.recall >= RECALL_THRESHOLD, report.render()
    assert report.permission_failures == 0, report.render()
    assert report.rrf_hits >= report.linear_hits, report.render()
    assert report.passed


def test_eval_permission_question_blocks_leak(
    db: DocumentDB, seed_docs: str, slack_export: str
) -> None:
    _ingest_seed(seed_docs, slack_export)
    report = run_eval()
    leak_rows = [r for r in report.rows if "leaked password" in r["question"]]
    assert leak_rows and all(r["ok"] for r in leak_rows)
