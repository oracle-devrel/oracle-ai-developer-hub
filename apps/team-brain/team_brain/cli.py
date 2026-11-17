"""team-brain command line.

team-brain ingest <source> [args...]   # e.g. markdown data/seed/docs | github owner/repo
team-brain ask "<question>" [--token T | --as USERNAME | --user U] [--project P]
team-brain eval                         # run golden-question retrieval eval
team-brain stats
team-brain serve                        # MCP over HTTP; callers send a bearer token
team-brain access seed                  # seed principals/groups/tokens; print tokens
team-brain principals
team-brain whoami --token T             # what the DATABASE resolved for this token
team-brain doctor                       # full end-to-end validation gate
"""

from __future__ import annotations

import argparse
import json
import sys

from team_brain.config import DEFAULT_USER


def _identity_from_args(args: argparse.Namespace) -> tuple[object, str]:
    """Three identity modes, all resolved by the database:

    --token  -> the MCP token path (fail closed on unknown tokens)
    --as     -> a seeded principal by username (its group grant is enforced)
    --user   -> a raw username with no domain grant (ACL-only, the legacy path)
    """
    from team_brain.access import Identity

    if getattr(args, "token", None):
        return Identity.token(args.token), f"token -> {args.token[:6]}..."
    if getattr(args, "as_principal", None):
        return Identity.principal(args.as_principal), f"principal {args.as_principal}"
    return Identity.user(args.user), f"user {args.user} (no domain grant)"


def _cmd_ingest(args: argparse.Namespace) -> int:
    from team_brain.ingest import ingest

    res = ingest(args.source, args.rest)
    print(
        f"[{res.source}] upserted={res.upserted} tombstoned={res.tombstoned} "
        f"fail_closed={res.skipped_fail_closed}"
    )
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    from team_brain.access import AccessControl, AccessError
    from team_brain.agent import answer
    from team_brain.db import DocumentDB

    identity, label = _identity_from_args(args)
    db = DocumentDB()
    try:
        try:
            db.set_identity(identity)  # type: ignore[arg-type]
        except AccessError as exc:
            print(f"error: {exc} (access denied)")
            return 1
        ac = AccessControl()
        try:
            p = ac.current_session_identity(db.connection, db.context_name)
        finally:
            ac.close()
        print(f"[identity] {p.describe()}  ({label}, {db.visible_count()} visible docs)\n")
        result = answer(args.question, project=args.project, db=db)
    finally:
        db.close()
    print(result["answer"])
    if result["citations"]:
        print("\nCitations:")
        for c in result["citations"]:
            print(f"  - [{c['source']}] {c['title']} {c['url']}")
    if result.get("experts"):
        print("\nWho knows:")
        for e in result["experts"]:
            print(f"  - {e['author']} ({e['doc_count']} docs)")
    return 0


def _cmd_whoami(args: argparse.Namespace) -> int:
    from team_brain.access import AccessControl, AccessError
    from team_brain.db import DocumentDB

    identity, label = _identity_from_args(args)
    db = DocumentDB()
    try:
        try:
            db.set_identity(identity)  # type: ignore[arg-type]
        except AccessError as exc:
            print(f"error: {exc} (access denied)")
            return 1
        ac = AccessControl()
        try:
            p = ac.current_session_identity(db.connection, db.context_name)
        finally:
            ac.close()
        print(f"{p.describe()}  ({label})")
        print(f"visible documents: {db.visible_count()}")
    finally:
        db.close()
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    from team_brain.db import DocumentDB

    db = DocumentDB()
    try:
        db.init_schema()
        print(json.dumps(db.stats(), indent=2))
    finally:
        db.close()
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from team_brain.evaluate import run_eval

    report = run_eval()
    print(report.render())
    return 0 if report.passed else 1


def _cmd_serve(args: argparse.Namespace) -> int:
    from team_brain.config import MCP_HOST, MCP_PORT
    from team_brain.mcp_server import main as serve

    print(f"team-brain MCP service on http://{MCP_HOST}:{MCP_PORT}/mcp  (bearer token per request)")
    serve("streamable-http")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    import subprocess

    from team_brain.config import REPO_DIR

    script = REPO_DIR / "scripts" / "validate.py"
    return subprocess.run([sys.executable, str(script)]).returncode


def _cmd_access_seed(args: argparse.Namespace) -> int:
    from team_brain.access import AccessControl, load_access_spec, seed_access
    from team_brain.config import REPO_DIR
    from team_brain.db import DocumentDB

    path = args.file or str(REPO_DIR / "data" / "seed" / "access.yaml")
    db = DocumentDB()
    try:
        db.init_schema()  # the package that reads these tables must exist
    finally:
        db.close()
    ac = AccessControl()
    try:
        tokens = seed_access(ac, load_access_spec(path))
        principals = ac.list_principals()
    finally:
        ac.close()
    print(f"Seeded {len(principals)} principals from {path}:\n")
    for p in principals:
        print(f"  {p.describe()}")
    print("\nMCP tokens (stdio: TEAM_BRAIN_TOKEN env; HTTP: Authorization: Bearer <token>):")
    for user, token in tokens.items():
        print(f"  {user:8} {token}")
    return 0


def _cmd_principals(args: argparse.Namespace) -> int:
    from team_brain.access import AccessControl

    ac = AccessControl()
    try:
        ac.init_schema()
        principals = ac.list_principals()
    finally:
        ac.close()
    if not principals:
        print("No principals seeded yet. Run: team-brain access seed")
        return 0
    for p in principals:
        print(p.describe())
    return 0


def _add_identity_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--token", default=None, help="MCP token -> the database resolves identity")
    p.add_argument("--as", dest="as_principal", default=None, help="a seeded principal username")
    p.add_argument("--user", default=DEFAULT_USER, help="raw identity (no domain grant)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="team-brain", description="Team knowledge base on Oracle AI Database"
    )
    sub = p.add_subparsers(dest="command", required=True)

    ing = sub.add_parser("ingest", help="Ingest a source")
    ing.add_argument("source")
    ing.add_argument("rest", nargs=argparse.REMAINDER, default=[])
    ing.set_defaults(func=_cmd_ingest)

    ask = sub.add_parser("ask", help="Ask a question")
    ask.add_argument("question")
    _add_identity_flags(ask)
    ask.add_argument("--project", default=None)
    ask.set_defaults(func=_cmd_ask)

    who = sub.add_parser("whoami", help="Show what the database resolves for an identity")
    _add_identity_flags(who)
    who.set_defaults(func=_cmd_whoami)

    ev = sub.add_parser("eval", help="Run golden-question eval")
    ev.set_defaults(func=_cmd_eval)

    st = sub.add_parser("stats", help="Show knowledge base stats")
    st.set_defaults(func=_cmd_stats)

    srv = sub.add_parser("serve", help="Run the MCP service over HTTP (bearer token per request)")
    srv.set_defaults(func=_cmd_serve)

    doc = sub.add_parser("doctor", help="Run the full validation gate")
    doc.set_defaults(func=_cmd_doctor)

    acc = sub.add_parser("access", help="Access-control admin")
    acc_sub = acc.add_subparsers(dest="access_command", required=True)
    acc_seed = acc_sub.add_parser("seed", help="Seed principals/groups/tokens; print tokens")
    acc_seed.add_argument(
        "--file", default=None, help="access spec yaml (default data/seed/access.yaml)"
    )
    acc_seed.set_defaults(func=_cmd_access_seed)

    princ = sub.add_parser("principals", help="List seeded identities and their domain grants")
    princ.set_defaults(func=_cmd_principals)

    return p


def main() -> int:
    # Windows consoles default to a legacy code page; force UTF-8 so output never
    # crashes on encoding.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI top-level: friendly error, no traceback
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
