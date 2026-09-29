"""Retrieval eval: measure quality instead of trusting it.

Runs each golden question through hybrid search AS a given identity and checks:
  * expected_source appears in top-k,
  * must_include phrase appears in a top-k result,
  * must_not_include phrase appears in NO result (permission / safety).

Reports recall@k and, to back the workshop's headline claim empirically, checks
that RRF recovers at least as many `must_include` hits as the naive linear blend.

Identity per question: `principal: jeff` (a seeded principal; the database
enforces its grant) or `user: alice` (raw username, ACL-only). Defaults to the
raw `demo` user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from team_brain.access import Identity
from team_brain.config import REPO_DIR
from team_brain.db import DocumentDB
from team_brain.retrieval import Evidence, _naive_linear_blend, search

K = 5
RECALL_THRESHOLD = 0.8
GOLDEN_PATH = REPO_DIR / "data" / "golden_questions.yaml"


@dataclass
class EvalReport:
    total: int = 0
    passed_count: int = 0
    recall: float = 0.0
    permission_failures: int = 0
    rrf_hits: int = 0
    linear_hits: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.recall >= RECALL_THRESHOLD
            and self.permission_failures == 0
            and self.rrf_hits >= self.linear_hits
        )

    def render(self) -> str:
        lines = ["Retrieval eval", "=" * 60]
        for r in self.rows:
            mark = "PASS" if r["ok"] else "FAIL"
            lines.append(f"[{mark}] {r['question'][:52]:52}  ({r['detail']})")
        lines.append("-" * 60)
        lines.append(f"recall@{K}:            {self.recall:.2f}  (threshold {RECALL_THRESHOLD})")
        lines.append(f"permission failures: {self.permission_failures}")
        lines.append(f"RRF must-include hits vs linear: {self.rrf_hits} vs {self.linear_hits}")
        lines.append("=" * 60)
        lines.append("RESULT: " + ("PASS" if self.passed else "FAIL"))
        return "\n".join(lines)


def _contains(results: list[Evidence], phrase: str) -> bool:
    p = phrase.lower()
    return any(p in (e.title + " " + e.body).lower() for e in results)


def _hits_for(results: list[Evidence], q: dict[str, Any]) -> bool:
    if "must_include" not in q:
        return True
    return _contains(results, q["must_include"])


def _identity_for(q: dict[str, Any]) -> Identity:
    if q.get("token"):
        return Identity.token(str(q["token"]))
    if q.get("principal"):
        return Identity.principal(str(q["principal"]))
    return Identity.user(str(q.get("user", "demo")))


def run_eval(golden_path: Path | None = None, db: DocumentDB | None = None) -> EvalReport:
    path = golden_path or GOLDEN_PATH
    questions: list[dict[str, Any]] = yaml.safe_load(path.read_text(encoding="utf-8"))
    report = EvalReport()
    owns = db is None
    db = db or DocumentDB()
    try:
        scored = 0
        for q in questions:
            identity = _identity_for(q)
            results = search(q["question"], identity, limit=K, db=db)
            ok = True
            details = []

            if "expected_source" in q:
                hit = any(e.source == q["expected_source"] for e in results)
                ok = ok and hit
                details.append(f"source={q['expected_source']}:{'y' if hit else 'n'}")
            if "must_include" in q:
                hit = _contains(results, q["must_include"])
                ok = ok and hit
                details.append(f"incl:{'y' if hit else 'n'}")
            if "must_not_include" in q:
                leaked = _contains(results, q["must_not_include"])
                if leaked:
                    report.permission_failures += 1
                ok = ok and not leaked
                details.append(f"safe:{'y' if not leaked else 'LEAK'}")

            if "expected_source" in q or "must_include" in q:
                scored += 1
                if ok:
                    report.passed_count += 1

            if "must_include" in q:
                if _hits_for(results, q):
                    report.rrf_hits += 1
                linear = _naive_linear_blend(q["question"], identity, limit=K, db=db)
                if _hits_for(linear, q):
                    report.linear_hits += 1

            report.rows.append({"question": q["question"], "ok": ok, "detail": ", ".join(details)})

        report.total = scored
        report.recall = (report.passed_count / scored) if scored else 0.0
        return report
    finally:
        if owns:
            db.close()
