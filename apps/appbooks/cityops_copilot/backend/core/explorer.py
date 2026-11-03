"""Read-only Data Explorer over the appbook's own tables.

Only tables under the appbook's prefix are listed, the browser never sends
SQL, and every value is bounded: at most 16 columns and 200 rows at a time,
vectors never leave the database, long text is cut to 300 characters.
"""

from __future__ import annotations

from . import db
from .lab import DROP_ORDER, Lab

MAX_COLUMNS = 16
MAX_ROWS = 200
FILTER_COLUMNS = (
    "USER_ID",
    "THREAD_ID",
    "AGENT_ID",
    "ASSET_ID",
    "MEMORY_TYPE",
    "MESSAGE_ROLE",
    "CATEGORY",
    "INSPECTOR",
)

# What each table is for, shown next to its name.
PURPOSE = {
    "ASSET": "Domain data · the asset registry (we create it)",
    "INSPECTION_FINDING": "Domain data · structured findings with a VECTOR(384) column (we create it)",
    "THREAD": "SDK · one row per conversation thread, with its scope and running summary",
    "MESSAGE": "SDK · every message, verbatim, in order (conversational history)",
    "MEMORY": "SDK · typed records the extractor distilled: fact, preference, guideline, memory",
    "RECORD_CHUNKS": "SDK · the embedded chunks behind memory search (vectors stay in the database)",
    "ACTOR_PROFILE": "SDK · user and agent profiles",
    "ORACLEAGENTMEMORY_SCHEMA_META": "SDK · its own schema version bookkeeping",
}


def allowlist(lab: Lab) -> dict[str, str]:
    return {lab.t(name): name for name in DROP_ORDER}


def tables(lab: Lab) -> list[dict]:
    allowed = allowlist(lab)
    existing = set(lab.existing_tables())
    out = []
    for table, short in allowed.items():
        if table not in existing:
            continue
        cols = columns(lab, table)
        out.append(
            {
                "table": table,
                "short": short,
                "purpose": PURPOSE.get(short, ""),
                "rows": int(db.scalar(lab.pool, f'SELECT COUNT(*) FROM "{table}"')),
                "columns": [{"name": c["column_name"].lower(), "type": c["type"]} for c in cols],
                "filters": [
                    c["column_name"].lower() for c in cols if c["column_name"] in FILTER_COLUMNS
                ],
            }
        )
    return out


def columns(lab: Lab, table: str) -> list[dict]:
    rows = db.query(
        lab.pool,
        """
        SELECT column_name, data_type, data_length, column_id
          FROM user_tab_columns WHERE table_name = :t ORDER BY column_id""",
        {"t": table},
    )
    for r in rows:
        r["type"] = r["data_type"] + (
            f"({int(r['data_length'])})" if r["data_type"] == "VARCHAR2" else ""
        )
    return rows


def rows(
    lab: Lab,
    table: str,
    *,
    limit: int = 50,
    offset: int = 0,
    filter_column: str | None = None,
    filter_value: str | None = None,
) -> dict:
    allowed = allowlist(lab)
    if table not in allowed:
        raise KeyError(f"{table} is not one of the appbook's tables")
    cols = columns(lab, table)[:MAX_COLUMNS]
    select = []
    for c in cols:
        name = c["column_name"]
        if c["data_type"] == "VECTOR":
            # Vectors never leave the database: show the dimension count instead.
            select.append(f"""'VECTOR(' || VECTOR_DIMENSION_COUNT("{name}") || ')' AS "{name}" """)
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
    order = (
        "ORDER BY order_seq DESC"
        if "ORDER_SEQ" in names
        else ("ORDER BY created_at DESC" if "CREATED_AT" in names else "")
    )
    limit = max(1, min(int(limit), MAX_ROWS))
    binds.update({"off": max(0, int(offset)), "lim": limit})
    sql = f'SELECT {", ".join(select)} FROM "{table}" {where} {order} OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY'
    data = db.query(lab.pool, sql, binds)
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
