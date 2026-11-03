"""Oracle access: one connection pool, small query helpers, JSON-safe values."""

from __future__ import annotations

import array
import datetime as dt
import decimal
import json
from typing import Any

import oracledb

from ..config import Settings

# Same as the notebook: CLOBs come back as str, JSON columns as dict/list.
oracledb.defaults.fetch_lobs = False

TEXT_LIMIT = 300  # Data Explorer cuts long text to this many characters


def create_pool(settings: Settings) -> oracledb.ConnectionPool:
    return oracledb.create_pool(
        user=settings.db_user,
        password=settings.db_password,
        dsn=settings.db_dsn,
        min=1,
        max=6,
        increment=1,
        # Fail fast instead of hanging when every connection is busy.
        getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
        wait_timeout=30_000,
        # Check each connection before handing it out, so a database restart
        # costs one reconnect instead of a failed request.
        ping_interval=0,
    )


def query(pool: oracledb.ConnectionPool, sql: str, binds: dict | None = None) -> list[dict]:
    with pool.acquire() as conn, conn.cursor() as cur:
        cur.execute(sql, binds or {})
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


def scalar(pool: oracledb.ConnectionPool, sql: str, binds: dict | None = None) -> Any:
    with pool.acquire() as conn, conn.cursor() as cur:
        cur.execute(sql, binds or {})
        row = cur.fetchone()
        return row[0] if row else None


def table_exists(pool: oracledb.ConnectionPool, name: str) -> bool:
    return bool(
        scalar(pool, "SELECT COUNT(*) FROM user_tables WHERE table_name = :n", {"n": name.upper()})
    )


def plain(value: Any, *, text_limit: int | None = None) -> Any:
    """Turn an Oracle value into something json.dumps accepts."""
    if value is None or isinstance(value, bool | int | str):
        if isinstance(value, str) and text_limit and len(value) > text_limit:
            return value[: text_limit - 1] + "…"
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, decimal.Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    if isinstance(value, array.array):
        return f"VECTOR({len(value)})"
    if isinstance(value, bytes | bytearray):
        return f"<{len(value)} bytes>"
    if isinstance(value, dict):
        return {k: plain(v, text_limit=text_limit) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [plain(v, text_limit=text_limit) for v in value]
    if hasattr(value, "read"):
        return plain(value.read(), text_limit=text_limit)
    return str(value)


def parse_json(value: Any) -> Any:
    if isinstance(value, dict | list) or value is None:
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value
