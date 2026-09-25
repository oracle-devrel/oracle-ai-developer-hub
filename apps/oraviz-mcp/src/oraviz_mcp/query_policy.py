"""Conservative SQL admission rules; database grants are the security boundary.

This deliberately accepts a subset of Oracle SELECT syntax. It is not a SQL
parser or a proof that a view, synonym, or built-in has no side effects.
"""

import re

MAX_SQL_CHARS = 32_000
_TOKEN = re.compile(
    r"(?P<space>\s+)|(?P<comment>--[^\n]*(?:\n|$)|/\*.*?\*/)"
    r"|(?P<string>'(?:''|[^'])*')|(?P<quoted>\"(?:\"\"|[^\"])*\")"
    r"|(?P<word>[A-Za-z_][A-Za-z0-9_$#]*)|(?P<number>\d+(?:\.\d+)?)"
    r"|(?P<symbol>[(),.*+\-/=<>&|!:;%@])",
    re.DOTALL,
)
_FORBIDDEN = frozenset(
    "INSERT UPDATE DELETE MERGE CREATE ALTER DROP TRUNCATE GRANT REVOKE "
    "BEGIN DECLARE EXECUTE CALL COMMIT ROLLBACK SAVEPOINT LOCK INTO "
    "FUNCTION PROCEDURE PRAGMA NEXTVAL CURRVAL".split()
)
# Review additions as code changes. Never take function names from a tool input.
_FUNCTIONS = frozenset(
    "COUNT SUM AVG MIN MAX MEDIAN STDDEV VARIANCE ROUND TRUNC ABS CEIL FLOOR "
    "MOD POWER SQRT EXP LN LOG SIGN NVL NVL2 NULLIF COALESCE DECODE CAST "
    "TO_CHAR TO_DATE TO_TIMESTAMP TO_NUMBER UPPER LOWER LENGTH SUBSTR TRIM "
    "LTRIM RTRIM REPLACE CONCAT INSTR REGEXP_LIKE REGEXP_REPLACE REGEXP_SUBSTR "
    "EXTRACT ADD_MONTHS MONTHS_BETWEEN LAST_DAY ROW_NUMBER RANK DENSE_RANK "
    "LAG LEAD FIRST_VALUE LAST_VALUE LISTAGG GROUPING GROUPING_ID "
    "VECTOR_DISTANCE COSINE_DISTANCE L2_DISTANCE INNER_PRODUCT TO_VECTOR "
    "FROM_VECTOR VECTOR_DIMENSION_COUNT VECTOR_DIMENSION_FORMAT".split()
)
_PAREN_KEYWORDS = frozenset(
    "AS IN EXISTS OVER PARTITION VALUES GROUPING SETS ROLLUP CUBE "
    "AND OR NOT WHEN THEN ELSE ON WHERE HAVING BY SELECT FROM JOIN".split()
)


def validate_query(query: str) -> str:
    """Admit one SELECT/CTE, rejecting writes, links, and unreviewed calls."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty")
    if len(query) > MAX_SQL_CHARS:
        raise ValueError(f"Query exceeds {MAX_SQL_CHARS} characters")
    query = query.strip()
    tokens = []
    pos = 0
    terminator = None
    while pos < len(query):
        match = _TOKEN.match(query, pos)
        if match is None:
            raise ValueError("Unsupported SQL syntax")
        kind, value = match.lastgroup, match.group()
        if query.startswith("/*", pos) and kind != "comment":
            raise ValueError("Unterminated SQL comment")
        if kind not in {"space", "comment"}:
            tokens.append((kind, value.upper() if kind == "word" else value))
            if value == ";":
                terminator = pos
        pos = match.end()

    if tokens and tokens[-1] == ("symbol", ";"):
        tokens.pop()
        # A trailing comment is allowed, but never forward the terminator.
        query = query[:terminator].rstrip()
    if not tokens or tokens[0] not in {("word", "SELECT"), ("word", "WITH")}:
        raise ValueError("Only read-only SELECT/WITH queries are allowed")

    depth = 0
    for index, (kind, value) in enumerate(tokens):
        if kind == "word" and value in _FORBIDDEN:
            raise ValueError("Only read-only SQL without side-effecting constructs is allowed")
        if kind == "quoted" and value[1:-1].upper() in {"NEXTVAL", "CURRVAL"}:
            raise ValueError("Sequence access is prohibited")
        if kind == "word" and value in {"Q", "NQ"} and index + 1 < len(tokens) and tokens[index + 1][0] == "string":
            raise ValueError("Alternative quoted strings are not supported; use standard SQL strings")
        if kind == "symbol" and value in {";", "@", ":"}:
            raise ValueError("Multiple statements, database links, and unbound parameters are prohibited")
        if value == "(" and kind == "symbol":
            depth += 1
            if depth > 32:
                raise ValueError("SQL nesting exceeds the limit")
            if index and tokens[index - 1][0] in {"word", "quoted"}:
                previous_kind, previous = tokens[index - 1]
                qualified = index > 1 and tokens[index - 2] == ("symbol", ".")
                if previous_kind == "quoted" or qualified or previous not in _FUNCTIONS | _PAREN_KEYWORDS:
                    raise ValueError("SQL function or construct is not on the reviewed allowlist")
        elif value == ")" and kind == "symbol":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced SQL parentheses")
    if depth:
        raise ValueError("Unbalanced SQL parentheses")
    return query
