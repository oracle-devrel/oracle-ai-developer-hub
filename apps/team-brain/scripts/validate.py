"""team-brain doctor — the one command that proves everything works (Oracle AI Database edition).

Waits for the Oracle AI Database Free container's TEAMBRAIN_TEST schema to be
reachable, runs the full static + test gate, then a REAL end-to-end smoke
(ingest -> access seed -> ask -> eval) with permission assertions. Exits
non-zero on any failure, with a PASS/FAIL/WARN summary and timings.

    uv run python scripts/validate.py     (or: uv run team-brain doctor)
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ORACLE_HOST = os.environ.get("ORACLE_HOST", "localhost")
ORACLE_PORT = int(os.environ.get("ORACLE_PORT", "1521"))
TEST_USER = os.environ.get("ORACLE_USER_TEST", "TEAMBRAIN_TEST")
TEST_PASSWORD = os.environ.get(
    "ORACLE_PASSWORD_TEST", os.environ.get("ORACLE_PASSWORD", "TeamBrain123")
)
_LIVE = bool(os.environ.get("TEAMBRAIN_LIVE"))

# Env for every child: point at the TEST schema, force offline determinism
# (unless TEAMBRAIN_LIVE), force UTF-8 output so nothing crashes on encoding.
ENV = {
    **os.environ,
    "ORACLE_USER": TEST_USER,
    "ORACLE_PASSWORD": TEST_PASSWORD,
    "LLM_API_KEY": os.environ.get("LLM_API_KEY", "") if _LIVE else "",
    "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", "") if _LIVE else "",
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "") if _LIVE else "",
    "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
    "PYTHONIOENCODING": "utf-8",
}

PY = sys.executable
results: list[tuple[str, bool, float]] = []
_WARN_ONLY: set[str] = set()


def _reconfigure() -> None:
    for stream in (sys.stdout, sys.stderr):
        fn = getattr(stream, "reconfigure", None)
        if fn:
            fn(encoding="utf-8", errors="replace")


def step(name: str, cmd: list[str], *, cwd: Path = REPO, warn_only: bool = False) -> bool:
    start = time.monotonic()
    print(f"\n>>> {name}\n    $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd), env=ENV)
    ok = proc.returncode == 0
    if warn_only:
        _WARN_ONLY.add(name)
    results.append((name, ok, time.monotonic() - start))
    label = "PASS" if ok else ("WARN" if warn_only else "FAIL")
    print(f"    {label} ({results[-1][2]:.1f}s)")
    return ok or warn_only


def wait_for_db(timeout: float = 60.0) -> bool:
    """TCP reachability is necessary but not sufficient; prove the TEAMBRAIN_TEST
    schema itself answers by creating its schema objects (idempotent)."""
    start = time.monotonic()
    print(
        f"\n>>> Waiting for Oracle AI Database at {ORACLE_HOST}:{ORACLE_PORT}/FREEPDB1 "
        f"(schema {TEST_USER})"
    )
    last_err: BaseException | None = None
    while time.monotonic() - start < timeout:
        try:
            with socket.create_connection((ORACLE_HOST, ORACLE_PORT), timeout=3):
                pass
            proc = subprocess.run(
                [
                    PY,
                    "-c",
                    "from team_brain.db import DocumentDB\n"
                    "d = DocumentDB(); d.init_schema(); d.close()",
                ],
                cwd=str(REPO),
                env=ENV,
            )
            if proc.returncode == 0:
                results.append((f"{TEST_USER} schema reachable", True, time.monotonic() - start))
                print(f"    PASS ({results[-1][2]:.1f}s)")
                return True
        except OSError as exc:
            last_err = exc
        time.sleep(2)
    results.append((f"{TEST_USER} schema reachable", False, time.monotonic() - start))
    print(f"    FAIL (timeout: {last_err})")
    return False


def smoke() -> bool:
    """Real ingest -> access seed -> ask -> eval, with permission assertions."""
    start = time.monotonic()
    print("\n>>> End-to-end smoke (ingest -> access seed -> ask -> eval + permission)")

    def cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PY, "-m", "team_brain.cli", *args],
            cwd=str(REPO),
            env=ENV,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    ok = True
    # fresh state
    reset = subprocess.run(
        [
            PY,
            "-c",
            "from team_brain.access import Identity\n"
            "from team_brain.db import DocumentDB\n"
            "d = DocumentDB()\n"
            "d.init_schema()\n"
            "d.set_identity(Identity.ingest())\n"
            "d.truncate()\n"
            "d.commit()\n"
            "d.close()\n",
        ],
        cwd=str(REPO),
        env=ENV,
    )
    ok = ok and reset.returncode == 0

    ok = ok and cli("ingest", "markdown", "data/seed/docs").returncode == 0
    ok = ok and cli("ingest", "slack", "--export", "data/seed/slack_export.json").returncode == 0
    ok = ok and cli("access", "seed").returncode == 0

    # alice (raw user, ACL-only): sees the public deploy runbook, never the
    # private security thread's secret.
    ask = cli("ask", "how do we deploy the billing service?", "--user", "alice")
    ok = ok and ask.returncode == 0
    if "blue-green" not in ask.stdout:
        print("    MISS: expected 'blue-green' in alice's answer")
        ok = False
    if "hunter2" in (ask.stdout + ask.stderr):
        print("    LEAK: restricted content reached a non-member (billing question)!")
        ok = False

    # adversarial: alice tries to fish for the secret directly.
    leak = cli("ask", "leaked password prod outage hunter2", "--user", "alice")
    if "hunter2" in (leak.stdout + leak.stderr):
        print("    LEAK: restricted content reached a non-member (direct fish)!")
        ok = False

    # jeff (ops-only principal, seeded by `access seed`): no sales content
    # exists in this corpus (only the base markdown+slack seed was ingested),
    # so this also proves domain scoping never fabricates a leak.
    sales = cli("ask", "what is our sales discount ceiling policy?", "--as", "jeff")
    ok = ok and sales.returncode == 0
    if "20%" in sales.stdout or "deal desk" in sales.stdout.lower():
        print("    LEAK: sales-only content reached an ops-only identity!")
        ok = False

    ev = cli("eval")
    ok = ok and ev.returncode == 0
    if ev.returncode != 0:
        print("    eval did not pass:\n" + ev.stdout[-2000:])

    results.append(("e2e smoke", ok, time.monotonic() - start))
    print(f"    {'PASS' if ok else 'FAIL'} ({results[-1][2]:.1f}s)")
    return ok


def main() -> int:
    _reconfigure()
    print("=" * 64)
    print("team-brain doctor — full validation gate (Oracle AI Database)")
    print("=" * 64)

    if not wait_for_db():
        return _summary()

    step("ruff check", [PY, "-m", "ruff", "check", "."])
    step("mypy", [PY, "-m", "mypy", "team_brain"], warn_only=True)
    step(
        "pytest (not live) + coverage",
        [
            PY,
            "-m",
            "pytest",
            "-m",
            "not live",
            "-p",
            "no:cacheprovider",
            "--cov=team_brain",
            "--cov-fail-under=80",
            "-q",
        ],
    )
    smoke()

    return _summary()


def _summary() -> int:
    print("\n" + "=" * 64)
    all_ok = True
    for name, ok, secs in results:
        mark = "PASS" if ok else ("WARN" if name in _WARN_ONLY else "FAIL")
        print(f"  [{mark}]  {name:40} {secs:6.1f}s")
        if not ok and name not in _WARN_ONLY:
            all_ok = False
    print("=" * 64)
    print("RESULT: " + ("ALL GREEN" if all_ok else "FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
