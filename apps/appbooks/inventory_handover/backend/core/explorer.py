"""Read-only Data Explorer over the appbook's OAMP store tables.

Only the appbook store's tables are listed, the browser never sends SQL, and
every value is bounded: at most 16 columns and 200 rows at a time, vectors
and blobs never leave the database, long text is cut to 300 characters.
"""

from __future__ import annotations

from . import db
from .lab import Lab

MAX_COLUMNS = 16
MAX_ROWS = 200
FILTER_COLUMNS = (
    "USER_ID",
    "THREAD_ID",
    "MEMORY_TYPE",
    "MESSAGE_ROLE",
    "STATUS",
    "RELATION_TYPE",
    "SOURCE_RECORD_TYPE",
    "ACTOR_TYPE",
)

# OAMP 26.8 table suffix -> what it holds (the order the list shows them in)
PURPOSE = {
    "THREAD": "one row per conversation/case thread: scope, metadata (workflow stage), runtime config",
    "MESSAGE": "episodic: every message verbatim (content as structured parts), with metadata and TTL",
    "MEMORY": "semantic + procedural: facts, preferences, guidelines, memories — with status and expiry",
    "MEMORY_LINK": "relationships between records, e.g. a current fact that supersedes an old one",
    "THREAD_SUMMARY": "the rolling summary OAMP keeps for a thread",
    "RECORD_CHUNKS": "embedded chunks behind vector search (vectors stay in the database)",
    "DOCUMENT": "attached documents (unused in this lab)",
    "ACTOR_PROFILE": "user and agent profiles (unused in this lab)",
}


def allowlist(lab: Lab) -> dict[str, str]:
    return {lab.t(suffix): suffix for suffix in PURPOSE}


def columns(lab: Lab, table: str) -> list[dict]:
    rows = db.query(
        lab.pool,
        """
        SELECT column_name, data_type, column_id FROM user_tab_columns WHERE table_name = :t ORDER BY column_id""",
        {"t": table},
    )
    return rows


def tables(lab: Lab) -> list[dict]:
    existing = set(lab.store_tables())
    out = []
    for table, suffix in allowlist(lab).items():
        if table not in existing:
            continue
        cols = columns(lab, table)
        out.append(
            {
                "table": table,
                "short": suffix,
                "purpose": PURPOSE[suffix],
                "rows": int(db.scalar(lab.pool, f'SELECT COUNT(*) FROM "{table}"')),
                "columns": [c["column_name"].lower() for c in cols],
                "filters": [
                    c["column_name"].lower() for c in cols if c["column_name"] in FILTER_COLUMNS
                ],
            }
        )
    return out


def rows(
    lab: Lab,
    table: str,
    *,
    limit: int = 50,
    offset: int = 0,
    filter_column: str | None = None,
    filter_value: str | None = None,
) -> dict:
    if table not in allowlist(lab):
        raise KeyError(f"{table} is not one of the appbook's tables")
    cols = columns(lab, table)[:MAX_COLUMNS]
    select = []
    for c in cols:
        name, kind = c["column_name"], c["data_type"]
        if kind == "VECTOR":
            select.append(f"""'VECTOR(' || VECTOR_DIMENSION_COUNT("{name}") || ')' AS "{name}" """)
        elif kind == "BLOB":
            select.append(
                f"""CASE WHEN "{name}" IS NULL THEN NULL ELSE '<' || DBMS_LOB.GETLENGTH("{name}") || ' bytes>' END AS "{name}" """
            )
        else:
            select.append(f'"{name}"')
    names = {c["column_name"] for c in cols}
    where, binds = "", {}
    if filter_column:
        fc = filter_column.upper()
        if fc not in FILTER_COLUMNS or fc not in names:
            raise KeyError(f"cannot filter {table} by {filter_column}")
        where = f'WHERE "{fc}" = :v'
        binds["v"] = filter_value
    order = next(
        (f"ORDER BY {c} DESC" for c in ("ORDER_SEQ", "CREATED_AT", "CHUNK_ID") if c in names), ""
    )
    limit = max(1, min(int(limit), MAX_ROWS))
    binds.update({"off": max(0, int(offset)), "lim": limit})
    data = db.query(
        lab.pool,
        f'SELECT {", ".join(select)} FROM "{table}" {where} {order} OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY',
        binds,
    )
    total = db.scalar(
        lab.pool, f'SELECT COUNT(*) FROM "{table}" {where}', {"v": filter_value} if where else {}
    )
    return {
        "table": table,
        "columns": [c["column_name"].lower() for c in cols],
        "rows": [db.plain(r, text_limit=db.TEXT_LIMIT) for r in data],
        "total": int(total),
        "offset": binds["off"],
        "limit": limit,
    }
