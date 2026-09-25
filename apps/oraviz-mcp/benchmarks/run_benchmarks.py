#!/usr/bin/env python
"""Token cost benchmark: oraviz-mcp vs the official Oracle SQLcl MCP server.

Both servers point at the same Oracle database and answer the same
questions. The harness measures the tokens an agent must process to get to
the answer: the tool schemas it reads once per session, plus every tool
result along the way. Charts are excluded from the token race (SQLcl MCP
has no chart tool); the chart step is reported separately as a capability.

Run with:  uv run --extra dev python benchmarks/run_benchmarks.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

try:
    import tiktoken
except ImportError:  # pragma: no cover - dev extra not installed
    tiktoken = None

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"

ENCODINGS = ("cl100k_base", "o200k_base")


@dataclass
class Step:
    name: str
    tool: str
    arguments: Dict[str, Any]
    setup: bool = False
    comparable: bool = True


@dataclass
class ServerSpec:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    steps: List[Step]


def build_scenarios(
    table: str, schema: str, sqlcl_command: str, sqlcl_connect: str
) -> List[ServerSpec]:
    """The same five questions for both servers (plus a fixed sqlcl connect)."""
    table_upper = table.upper()
    aggregate_sql = (
        f"SELECT region, SUM(revenue) AS total_revenue FROM {table} "
        f"WHERE sale_month >= (SELECT ADD_MONTHS(TRUNC(MAX(sale_month), 'MM'), -5) FROM {table}) "
        "GROUP BY region ORDER BY total_revenue DESC"
    )
    describe_sql = (
        "SELECT column_name, data_type, data_length, nullable "
        f"FROM user_tab_columns WHERE table_name = '{table_upper}' ORDER BY column_id"
    )

    oraviz_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "ORACLE_USER": os.environ["ORAVIZ_BENCH_USER"],
        "ORACLE_PASSWORD": os.environ["ORAVIZ_BENCH_PASSWORD"],
        "ORACLE_DSN": os.environ["ORAVIZ_BENCH_DSN"],
    }
    sqlcl_env = {
        "PATH": "/usr/bin:/bin",
        "JAVA_HOME": os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-21-openjdk-amd64"),
    }

    oraviz = ServerSpec(
        name="oraviz-mcp",
        command="uv",
        args=["run", "--directory", str(REPO_ROOT), "oraviz-mcp"],
        env=oraviz_env,
        steps=[
            Step("list objects", "list_tables", {}),
            Step("describe table", "get_table_schema", {"table_name": table}),
            Step("aggregate revenue by region", "execute_query", {"query": aggregate_sql}),
            Step("sample 10 rows", "sample_table_data", {"table_name": table, "sample_size": 10}),
            Step("raw 96-row dump", "execute_query", {"query": f"SELECT * FROM {table}"}),
            Step(
                "chart the aggregate (result set to PNG)",
                "create_chart",
                {
                    "sql": aggregate_sql,
                    "chart_type": "bar",
                    "title": "Revenue by region, last 6 months",
                },
                comparable=False,
            ),
        ],
    )
    sqlcl = ServerSpec(
        name="sqlcl-mcp",
        command=sqlcl_command,
        args=["-mcp"],
        env=sqlcl_env,
        steps=[
            Step("connect", "run-sqlcl", {"sqlcl": f"connect {sqlcl_connect}"}, setup=True),
            Step("list objects", "schema-information", {"schema": schema.upper()}),
            Step("describe table", "run-sql", {"sql": describe_sql}),
            Step("aggregate revenue by region", "run-sql", {"sql": aggregate_sql}),
            Step(
                "sample 10 rows",
                "run-sql",
                {"sql": f"SELECT * FROM {table} FETCH FIRST 10 ROWS ONLY"},
            ),
            Step("raw 96-row dump", "run-sql", {"sql": f"SELECT * FROM {table}"}),
        ],
    )
    return [oraviz, sqlcl]


def encoders() -> Dict[str, Any]:
    if tiktoken is None:
        raise SystemExit(
            "tiktoken is required for the benchmark: install the dev extra (uv sync --extra dev)"
        )
    return {name: tiktoken.get_encoding(name) for name in ENCODINGS}


def count_tokens(encs: Dict[str, Any], text: str) -> Dict[str, int]:
    return {name: len(encoder.encode(text)) for name, encoder in encs.items()}


def tool_schema_text(tools: List[Any]) -> str:
    payload = []
    for tool in tools:
        payload.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": getattr(tool, "input_schema", None)
                or getattr(tool, "inputSchema", None),
            }
        )
    return json.dumps(payload, sort_keys=True)


def result_text(result: Any) -> str:
    texts = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    return "\n".join(texts)


async def measure_server(spec: ServerSpec, encs: Dict[str, Any]) -> Dict[str, Any]:
    transport = StdioTransport(command=spec.command, args=spec.args, env=spec.env, keep_alive=False)
    measurements: List[Dict[str, Any]] = []
    async with Client(transport) as client:
        tools = await client.list_tools()
        schema_tokens = count_tokens(encs, tool_schema_text(tools))
        print(
            f"[{spec.name}] {len(tools)} tools, schema tokens: "
            + ", ".join(f"{key}={value}" for key, value in schema_tokens.items()),
            file=sys.stderr,
        )
        for step in spec.steps:
            result = await client.call_tool(step.tool, step.arguments)
            text = result_text(result)
            tokens = count_tokens(encs, text)
            measurements.append(
                {
                    "step": step.name,
                    "tool": step.tool,
                    "setup": step.setup,
                    "comparable": step.comparable,
                    "tokens": tokens,
                    "chars": len(text),
                }
            )
            print(
                f"[{spec.name}] {step.name}: "
                + ", ".join(f"{key}={value}" for key, value in tokens.items())
                + f" ({len(text)} chars)",
                file=sys.stderr,
            )
    answer_tokens = {
        name: schema_tokens[name]
        + sum(m["tokens"][name] for m in measurements if not m["setup"] and m["comparable"])
        for name in ENCODINGS
    }
    setup_tokens = {
        name: sum(m["tokens"][name] for m in measurements if m["setup"]) for name in ENCODINGS
    }
    return {
        "server": spec.name,
        "schema_tokens": schema_tokens,
        "setup_tokens": setup_tokens,
        "steps": measurements,
        "answer_tokens": answer_tokens,
        "grand_total": {name: answer_tokens[name] + setup_tokens[name] for name in ENCODINGS},
    }


def savings(official: int, ours: int) -> float:
    return round((official - ours) / official * 100, 1) if official else 0.0


def build_report(servers: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_name = {entry["server"]: entry for entry in servers}
    oraviz, sqlcl = by_name["oraviz-mcp"], by_name["sqlcl-mcp"]

    comparison: Dict[str, Any] = {}
    for encoding in ENCODINGS:
        step_savings = {}
        for step in oraviz["steps"]:
            if not step["comparable"]:
                continue
            match = next(m for m in sqlcl["steps"] if m["step"] == step["step"])
            step_savings[step["step"]] = savings(match["tokens"][encoding], step["tokens"][encoding])
        comparison[encoding] = {
            "schema_tokens": {
                "oraviz-mcp": oraviz["schema_tokens"][encoding],
                "sqlcl-mcp": sqlcl["schema_tokens"][encoding],
                "savings_pct": savings(
                    sqlcl["schema_tokens"][encoding], oraviz["schema_tokens"][encoding]
                ),
            },
            "answer_tokens": {
                "oraviz-mcp": oraviz["answer_tokens"][encoding],
                "sqlcl-mcp": sqlcl["answer_tokens"][encoding],
                "savings_pct": savings(
                    sqlcl["answer_tokens"][encoding], oraviz["answer_tokens"][encoding]
                ),
            },
            "grand_total": {
                "oraviz-mcp": oraviz["grand_total"][encoding],
                "sqlcl-mcp": sqlcl["grand_total"][encoding],
                "savings_pct": savings(
                    sqlcl["grand_total"][encoding], oraviz["grand_total"][encoding]
                ),
            },
            "step_savings_pct": step_savings,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "encodings": list(ENCODINGS),
        "servers": servers,
        "comparison": comparison,
    }


def markdown_report(report: Dict[str, Any]) -> str:
    primary = "cl100k_base"
    oraviz = next(s for s in report["servers"] if s["server"] == "oraviz-mcp")
    sqlcl = next(s for s in report["servers"] if s["server"] == "sqlcl-mcp")
    steps = report["comparison"][primary]["step_savings_pct"]

    lines = [
        "# Token benchmark: oraviz-mcp vs the official SQLcl MCP server",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "Token counts use `tiktoken` (`cl100k_base`; `o200k_base` numbers are in the JSON).",
        "Lower is better; savings are relative to the official SQLcl MCP server.",
        "Negative savings mean the official server used fewer tokens for that step.",
        "",
        "| Question | oraviz-mcp | sqlcl-mcp | Savings |",
        "|---|---:|---:|---:|",
    ]
    for step in oraviz["steps"]:
        if step["setup"] or not step["comparable"]:
            continue
        match = next(m for m in sqlcl["steps"] if m["step"] == step["step"])
        lines.append(
            f"| {step['step']} | {step['tokens'][primary]} | {match['tokens'][primary]} "
            f"| {steps[step['step']]:.1f}% |"
        )

    lines += ["", "| Aggregate | oraviz-mcp | sqlcl-mcp | Savings |", "|---|---:|---:|---:|"]
    for label, key in (
        ("Tool schemas (read once per session)", "schema_tokens"),
        ("Tool results to answer the questions", "answer_tokens"),
        ("Total", "grand_total"),
    ):
        row = report["comparison"][primary][key]
        lines.append(
            f"| {label} | {row['oraviz-mcp']} | {row['sqlcl-mcp']} | {row['savings_pct']:.1f}% |"
        )
    lines.append(
        f"| sqlcl-only setup (connect step) | 0 | {sqlcl['setup_tokens'][primary]} | 100.0% |"
    )
    extra = [step for step in oraviz["steps"] if not step["comparable"]]
    if extra:
        lines += [
            "",
            "## Capability add-on (not part of the token race)",
            "",
            "SQLcl MCP has no chart tool, so these steps cannot be compared; they are reported",
            "for reference (image bytes are a different modality and are not counted as text tokens).",
            "",
            "| Step | oraviz-mcp text tokens | sqlcl-mcp |",
            "|---|---:|---:|",
        ]
        for step in extra:
            lines.append(
                f"| {step['step']} | {step['tokens'][primary]} (+ PNG image) | n/a |"
            )
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn", default=os.environ.get("ORAVIZ_BENCH_DSN", "localhost:1530/FREEPDB1")
    )
    parser.add_argument("--user", default=os.environ.get("ORAVIZ_BENCH_USER", "oraviz"))
    parser.add_argument("--password", default=os.environ.get("ORAVIZ_BENCH_PASSWORD", "OraViz2026"))
    parser.add_argument("--table", default="sales_demo")
    parser.add_argument(
        "--schema", default=None, help="schema that owns the table (default: the user)"
    )
    parser.add_argument(
        "--sqlcl", default=os.environ.get("SQLCL_BIN", "/home/ubuntu/opt/sqlcl/bin/sql")
    )
    parser.add_argument("--json-out", default=str(RESULTS_DIR / "benchmark-results.json"))
    parser.add_argument("--md-out", default=str(RESULTS_DIR / "benchmark-results.md"))
    args = parser.parse_args()

    os.environ["ORAVIZ_BENCH_DSN"] = args.dsn
    os.environ["ORAVIZ_BENCH_USER"] = args.user
    os.environ["ORAVIZ_BENCH_PASSWORD"] = args.password

    encs = encoders()
    specs = build_scenarios(
        table=args.table,
        schema=args.schema or args.user,
        sqlcl_command=args.sqlcl,
        sqlcl_connect=f"{args.user}/{args.password}@{args.dsn}",
    )

    servers = []
    for spec in specs:
        servers.append(await measure_server(spec, encs))

    report = build_report(servers)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(report, indent=2) + "\n")
    Path(args.md_out).write_text(markdown_report(report) + "\n")

    primary = ENCODINGS[0]
    print("\n" + markdown_report(report))
    print(f"JSON: {args.json_out}\nMarkdown: {args.md_out}")
    print(
        "Headline savings: "
        f"{report['comparison'][primary]['grand_total']['savings_pct']:.1f}% total, "
        f"{report['comparison'][primary]['answer_tokens']['savings_pct']:.1f}% on results alone"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
