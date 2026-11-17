"""Run the retrieval eval against the FULL Acme Ledger golden question set.

`team_brain.evaluate.run_eval()` hardcodes GOLDEN_PATH to
data/golden_questions.yaml, but it accepts an override — this script is that
override, pointed at data/golden_questions_full.yaml (37 questions over the
data/seed_full/ knowledge base). No team_brain/ file is touched.

Also reports a stricter bar (recall >= 0.9, zero permission failures)
alongside team_brain.evaluate's built-in 0.8 threshold.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
GOLDEN_FULL = REPO_DIR / "data" / "golden_questions_full.yaml"
OUR_RECALL_BAR = 0.9


def main() -> int:
    from team_brain.evaluate import run_eval

    report = run_eval(golden_path=GOLDEN_FULL)
    print(report.render())
    print()
    ok = report.recall >= OUR_RECALL_BAR and report.permission_failures == 0
    print(f"Strict bar: recall >= {OUR_RECALL_BAR} AND permission_failures == 0")
    print(f"  recall:              {report.recall:.3f}")
    print(f"  permission_failures: {report.permission_failures}")
    print(f"  RRF vs linear hits:  {report.rrf_hits} vs {report.linear_hits}")
    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
