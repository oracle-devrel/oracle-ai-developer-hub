"""MCP server: SEARCH PRIMITIVES, exposed to a PER-CALLER IDENTITY the database enforces.

Two design choices, both straight from the workshop's argument:

1. Primitives, not an answer endpoint. Ship `search`, `search_code`, `who_knows`,
   low-level tools that return raw evidence rows, and let each caller's own agent
   orchestrate and synthesize. A server that synthesized answers would impose ONE
   voice on every consumer. Personality lives in the client; policy (enrichment,
   ranking, PERMISSIONS) lives here. Centralize the policy, distribute the
   personality.

2. Identity lives in the database, not in the agent and not in this process.
   Every request establishes its caller on a fresh database session through the
   trusted `tb_session` package, and the row policy filters every read. This
   server holds the database credential; callers hold tokens. A caller with the
   wrong token is refused inside the database (ORA-20402). A session with no
   identity gets zero rows. There is no code path here that decides who sees
   what; there is nothing to talk a model out of.

Two transports, same tools:

  stdio  (local, one identity per process)
      TEAM_BRAIN_TOKEN=... uv run python -m team_brain.mcp_server
      Wire into Claude Code via .mcp.json (copy .mcp.json.example) with the token in `env`.

  streamable-http  (remote service, one identity per REQUEST)
      uv run team-brain serve            # http://127.0.0.1:8765/mcp
      Clients send `Authorization: Bearer <token>`; the client config holds
      only the URL and the token, never the database credential.

Token -> identity (POC): a static opaque token maps to a principal (see
team_brain/access.py, seeded from data/seed/access.yaml). A production deployment
would issue short-lived, audience-bound tokens from an identity provider; the
enforcement model is identical.
"""

from __future__ import annotations

import contextlib
import faulthandler
import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

# Loading the LangChain legs here (and numpy's native extension with them) is
# deliberate: it must happen in the main thread at startup, not lazily inside
# the first tool call. See langchain_legs.py.
import team_brain.langchain_legs  # noqa: F401
from team_brain.access import AccessControl, AccessError, Identity
from team_brain.agent import _run_search_code
from team_brain.config import MCP_HOST, MCP_PORT
from team_brain.db import DocumentDB
from team_brain.retrieval import search as _search

# A hard crash (native code, oracledb, ONNX) would otherwise kill the server with
# no trace on the stdio transport.
faulthandler.enable(file=sys.stderr)

mcp = FastMCP("team-brain", host=MCP_HOST, port=MCP_PORT)

_TOKEN_ENV = "TEAM_BRAIN_TOKEN"


def _http_request(ctx: Context[Any, Any, Any] | None) -> Any | None:
    """The HTTP request behind this tool call, or None on the stdio transport."""
    if ctx is None:
        return None
    try:
        return ctx.request_context.request
    except (AttributeError, ValueError):
        return None


def _token_from_request(request: Any) -> str | None:
    """Bearer token from an HTTP request; None when the header is absent or malformed."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def _identity_for(ctx: Context[Any, Any, Any] | None) -> Identity:
    """HTTP: the request's bearer token, nothing else. stdio: TEAM_BRAIN_TOKEN. Neither: anonymous.

    Over HTTP the process environment is never consulted: a request without a
    bearer header is anonymous even if the operator exported a token for stdio.
    Anonymous is a real identity with no grant: public, company-wide rows only.
    A supplied-but-unknown token is refused by the database, never downgraded.
    """
    request = _http_request(ctx)
    if request is not None:
        token = _token_from_request(request)
    else:
        token = os.environ.get(_TOKEN_ENV, "").strip() or None
    return Identity.token(token) if token else Identity.anonymous()


_MAX_LIMIT = 50


def _clamp(limit: int) -> int:
    return max(1, min(int(limit), _MAX_LIMIT))


@contextmanager
def _session(ctx: Context[Any, Any, Any] | None) -> Iterator[DocumentDB]:
    """A database session with THIS caller's identity established, closed after use.

    stdout is the MCP wire on the stdio transport, and Oracle's LangChain vector
    store prints a "Database version" line when it is constructed. Everything a
    tool does runs with stdout pointed at stderr so nothing can corrupt the stream.
    """
    db = DocumentDB()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            try:
                db.set_identity(_identity_for(ctx))
            except AccessError as exc:
                raise AccessError(
                    f"{exc}. Access denied. Run `team-brain access seed` and use one of the "
                    "printed tokens."
                ) from exc
            try:
                yield db
            except Exception:
                logging.getLogger(__name__).exception("tool failed")
                raise
    finally:
        db.close()


@mcp.tool()
def whoami(ctx: Context[Any, Any, Any]) -> dict[str, Any]:
    """Show the identity this connection resolved to and the domains it may read."""
    with _session(ctx) as db:
        ac = AccessControl()
        try:
            p = ac.current_session_identity(db.connection, db.context_name)
        finally:
            ac.close()
        return {
            "username": p.username,
            "display_name": p.display_name,
            "domains": "ALL" if p.all_domains else sorted(p.domains),
            "visible_documents": db.visible_count(),
        }


@mcp.tool()
def search(
    query: str, ctx: Context[Any, Any, Any], project: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Search the team knowledge base across all sources you're permitted to see."""
    with _session(ctx) as db:
        return [e.to_row() for e in _search(query, project=project, limit=_clamp(limit), db=db)]


@mcp.tool()
def search_code(
    query: str, ctx: Context[Any, Any, Any], project: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Search only code and repository knowledge you're permitted to see."""
    with _session(ctx) as db:
        return [e.to_row() for e in _run_search_code(query, project, db)[:limit]]


@mcp.tool()
def get_document(row_id: str, ctx: Context[Any, Any, Any]) -> dict[str, Any]:
    """Full text of one search result by its `id` (search rows carry a 240-char snippet).

    Returns {"found": false} when the row does not exist OR the caller may not see it;
    the database decides which and does not say.
    """
    with _session(ctx) as db:
        row = db.get_document(row_id)
        if row is None:
            return {"found": False, "id": row_id}
        md = row.get("metadata") or {}
        return {
            "found": True,
            "id": row["id"],
            "source": row["source"],
            "title": row["title"],
            "url": row["url"],
            "author": row["author"],
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "domains": list(md.get("domains") or []),
            "text": row["body"],
        }


@mcp.tool()
def who_knows(
    topic: str, ctx: Context[Any, Any, Any], project: str | None = None, limit: int = 5
) -> list[dict[str, Any]]:
    """Find who owns/knows the most about a topic (ranked authors of matching docs)."""
    with _session(ctx) as db:
        return db.who_knows(topic, project, _clamp(limit))


def main(transport: str = "stdio") -> None:
    dump_every = os.environ.get("TEAM_BRAIN_DEBUG_DUMP")
    if dump_every:
        # Debug aid: dump every thread's stack to stderr on an interval.
        faulthandler.dump_traceback_later(int(dump_every), repeat=True, file=sys.stderr)
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main(os.environ.get("TEAM_BRAIN_TRANSPORT", "stdio"))
