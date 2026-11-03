"""Offline contracts: no database, no model.

Run from the appbook folder:  python -m pytest tests/test_contracts.py -q
"""

from __future__ import annotations

import ast
import asyncio
import os
import random
import re
from pathlib import Path

import pytest

APPBOOK = Path(__file__).resolve().parents[1]
os.environ["DBPASSWORD"] = ""  # the runtime must fail fast and say why
os.environ.setdefault("DB_DSN", "localhost:1/NOPE")

from backend import config  # noqa: E402
from backend.core import explorer  # noqa: E402
from backend.core.jobs import Job, JobManager  # noqa: E402
from backend.core.lab import DROP_ORDER, Lab, TracingLlm, _purpose, classify_asset  # noqa: E402
from backend.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # wait for the background start to fail on the missing password
        for _ in range(50):
            if "password" in (c.get("api/health").json().get("error") or ""):
                break
            asyncio.run(asyncio.sleep(0.05))
        yield c


def lab_offline() -> Lab:
    return Lab(config.load_settings(), JobManager())


# ------------------------------------------------------------------ settings


def test_prefix_rules(monkeypatch):
    monkeypatch.setenv("APPBOOK_TABLE_PREFIX", "CITY_")
    with pytest.raises(ValueError):
        config.load_settings()
    monkeypatch.setenv("APPBOOK_TABLE_PREFIX", "bad prefix")
    with pytest.raises(ValueError):
        config.load_settings()
    monkeypatch.setenv("APPBOOK_TABLE_PREFIX", "cityapp_")
    assert config.load_settings().table_prefix == "CITYAPP_"


def test_notebook_and_appbook_link_each_other():
    """The notebook sits in notebooks/agent_memory/cityops_copilot/ and links to this appbook; the appbook links back."""
    notebook = (config.NOTEBOOK_DIR / config.NOTEBOOK_FILE).read_text()
    assert "apps/appbooks/cityops_copilot" in notebook
    assert config.NOTEBOOK_URL.endswith(
        f"notebooks/agent_memory/cityops_copilot/{config.NOTEBOOK_FILE}"
    )
    assert config.NOTEBOOK_URL in (APPBOOK / "frontend/app.js").read_text()
    assert config.NOTEBOOK_FILE in (APPBOOK / "README.md").read_text()


def test_defaults_match_the_notebook(monkeypatch):
    for k in (
        "DBUSER",
        "DB_DSN",
        "ONNX_MODEL",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "DEMO_FINDING_COUNT",
    ):
        monkeypatch.delenv(k, raising=False)
    s = config.load_settings()
    assert (s.db_user, s.db_dsn, s.onnx_model) == (
        "prism",
        "localhost:1522/FREEPDB1",
        "ALL_MINILM_L12_V2",
    )
    assert (s.ollama_base_url, s.ollama_model, s.demo_finding_count) == (
        "http://localhost:11434",
        "llama3.2",
        15,
    )
    assert (s.data_dir / "maintenance_logs.json").exists()


# ------------------------------------------------------------- notebook code


def test_every_sql_statement_uses_the_prefix():
    """No SQL in lab.py may name a notebook table (CITY_…) directly."""
    tree = ast.parse((APPBOOK / "backend/core/lab.py").read_text())
    sql_re = re.compile(r"\b(SELECT|INSERT|CREATE|DROP|FROM|INTO|UPDATE|DELETE)\b")
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            parts = "".join(
                v.value
                for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            parts = node.value
        else:
            continue
        if sql_re.search(parts) and re.search(r"\bCITY_[A-Z]", parts):
            offenders.append(parts[:80])
    assert not offenders, offenders


def test_reset_only_names_prefixed_tables():
    lab = lab_offline()
    names = [lab.t(n) for n in DROP_ORDER]
    assert all(n.startswith(lab.s.table_prefix) and not n.startswith("CITY_") for n in names)
    assert names[0].endswith(
        "INSPECTION_FINDING"
    )  # child table before its parent, as in the notebook


def test_asset_classes_follow_the_notebook_rule():
    assert classify_asset("Harbor Bridge") == "bridge"
    assert classify_asset("Meridian Overpass") == "bridge"
    assert classify_asset("Northgate Substation") == "substation"
    assert classify_asset("Seawall Section 4") == "civil"
    lab = lab_offline()
    assert len(lab.equipment) == 26


def test_sample_matches_the_notebook():
    """sample_narratives uses Random(42); the notebook calls random.seed(42). Same picks."""
    lab = lab_offline()
    random.seed(42)
    buckets = {"routine": [], "warning": [], "critical": []}
    for log in lab.logs:
        buckets.get(log["severity"], []).append(log)
    n = 4
    expect = (
        random.sample(buckets["routine"], max(1, n // 2))
        + random.sample(buckets["warning"], max(1, n // 3))
        + random.sample(buckets["critical"], max(1, n - n // 2 - n // 3))
    )[:n]
    assert lab.sample_narratives(4) == expect


def test_llm_purposes():
    assert (
        _purpose(
            [
                {
                    "role": "system",
                    "content": "You are a memory extraction module… preference … guideline",
                }
            ],
            None,
        )
        == "memory extraction"
    )
    assert _purpose("Return JSON only with: summary … topics", None) == "context-card summary"
    assert _purpose("hello", None) == "SDK LLM call"


def test_tracing_llm_records_on_the_running_job():
    class Inner:
        def generate(self, prompt, response_json_schema=None, **kw):
            from oracleagentmemory.apis.llms.llm import LlmResponse

            return LlmResponse(text="ok")

        async def generate_async(self, prompt, response_json_schema=None, **kw):
            return self.generate(prompt)

    jobs = JobManager()
    job = Job("t", "t", [("a", "A")])
    jobs.current = job
    job.begin("a")
    llm = TracingLlm(Inner(), jobs)
    llm.generate("summary and topics please")
    asyncio.run(llm.generate_async([{"role": "user", "content": "x"}]))
    assert [c["purpose"] for c in job.llm_calls] == ["context-card summary", "SDK LLM call"]
    assert job.llm_calls[0]["step"] == "a" and job.llm_calls[0]["who"] == "sdk"


# --------------------------------------------------------------------- jobs


def test_jobs_run_one_at_a_time_and_capture_errors():
    async def scenario():
        jm = JobManager()
        order = []

        async def slow(j):
            order.append("a-start")
            await asyncio.sleep(0.05)
            order.append("a-end")
            return 1

        async def boom(j):
            order.append("b-start")
            j.begin("x")
            raise RuntimeError("bad")

        a = jm.submit(Job("a", "a"), slow)
        b = jm.submit(Job("b", "b", [("x", "X")]), boom)
        while b.status not in ("done", "error"):
            await asyncio.sleep(0.01)
        return order, a, b

    order, a, b = asyncio.run(scenario())
    assert order == ["a-start", "a-end", "b-start"]
    assert a.status == "done" and a.result == 1
    assert b.status == "error" and "bad" in b.error and b.steps[0]["status"] == "error"


def test_prompts_are_bounded():
    job = Job("t", "t")
    job.record_llm("agent", "p", [{"role": "user", "content": "x" * 50_000}], "r", 1)
    assert len(job.llm_calls[0]["messages"][0]["content"]) < 21_000


# ----------------------------------------------------------------- explorer


def test_explorer_allowlist_and_filters():
    lab = lab_offline()
    allowed = explorer.allowlist(lab)
    assert set(allowed) == {lab.t(n) for n in DROP_ORDER}
    with pytest.raises(KeyError):
        explorer.rows(lab, "CITY_MEMORY")  # the notebook's table: not browsable
    with pytest.raises(KeyError):
        explorer.rows(lab, "USER_TABLES")
    assert "CONTENT" not in explorer.FILTER_COLUMNS  # filters only on id-like columns
    assert explorer.MAX_ROWS == 200 and explorer.MAX_COLUMNS == 16


# --------------------------------------------------------------------- API


EXPECTED_ROUTES = {
    ("GET", "/api/health"),
    ("POST", "/api/reconnect"),
    ("GET", "/api/overview"),
    ("POST", "/api/reset"),
    ("GET", "/api/jobs"),
    ("GET", "/api/jobs/{job_id}"),
    ("POST", "/api/embed"),
    ("GET", "/api/assets"),
    ("GET", "/api/narratives"),
    ("POST", "/api/report-event"),
    ("POST", "/api/extraction-demo"),
    ("GET", "/api/memories"),
    ("GET", "/api/messages"),
    ("GET", "/api/threads"),
    ("POST", "/api/search"),
    ("GET", "/api/findings"),
    ("POST", "/api/findings/search"),
    ("POST", "/api/findings/log"),
    ("POST", "/api/findings/load-all"),
    ("POST", "/api/scoping-demo"),
    ("POST", "/api/copilot"),
    ("POST", "/api/stateless"),
    ("GET", "/api/handoff"),
    ("POST", "/api/handoff/{step}"),
    ("GET", "/api/explorer/tables"),
    ("GET", "/api/explorer/rows"),
}


def test_routes():
    # The OpenAPI schema lists every route, however the FastAPI version nests included routers.
    have = {(m.upper(), path) for path, ops in app.openapi()["paths"].items() for m in ops}
    assert EXPECTED_ROUTES <= have, EXPECTED_ROUTES - have


def test_health_explains_a_missing_password(client):
    h = client.get("api/health").json()
    assert h["ready"] is False and "DBPASSWORD" in h["error"]
    assert h["prefix"] == "CITYAPP_" and h["db"]["password_set"] is False


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "api/overview", None),
        ("get", "api/assets", None),
        ("post", "api/embed", {"texts": ["a"]}),
        (
            "post",
            "api/copilot",
            {"narrative": "rust on pier", "inspector_id": "x", "asset_id": "Harbor Bridge"},
        ),
        ("get", "api/explorer/tables", None),
    ],
)
def test_live_routes_refuse_until_ready(client, method, path, body):
    r = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
    assert r.status_code == 503 and "DBPASSWORD" in r.json()["detail"]


@pytest.mark.parametrize(
    "path,body",
    [
        ("api/copilot", {"narrative": "x" * 5000, "inspector_id": "a", "asset_id": "b"}),
        ("api/copilot", {"narrative": "ok ok", "inspector_id": "", "asset_id": "b"}),
        ("api/findings/search", {"description": "x", "k": 50}),
        (
            "api/findings/log",
            {
                "asset_id": "a",
                "inspector": "b",
                "category": "c",
                "severity": "huge",
                "description": "ddd",
            },
        ),
        ("api/embed", {"texts": ["a", "b", "c", "d", "e"]}),
        ("api/search", {"query": "q", "record_types": ["secret"]}),
        ("api/extraction-demo", {"count": 99}),
    ],
)
def test_request_bodies_are_bounded(client, path, body):
    assert client.post(path, json=body).status_code == 422


def test_unknown_job_is_404(client):
    assert client.get("api/jobs/nope").status_code == 404


# ------------------------------------------------------------------ frontend


def test_frontend_uses_relative_urls_only():
    """Relative URLs keep the page working under any path prefix."""
    index = (APPBOOK / "frontend/index.html").read_text()
    assert not re.search(r'(src|href)="/(?!/)', index), "index.html must use relative URLs"
    for js in (APPBOOK / "frontend").glob("*.js"):
        text = js.read_text()
        assert not re.search(r"""fetch\(\s*['"`]/""", text), f"{js.name} fetches an absolute path"
        assert not re.search(r"""['"`]/api/""", text), f"{js.name} uses /api/ instead of api/"
    for src in re.findall(r'<script src="([^"]+)"', index):
        assert (APPBOOK / "frontend" / src).exists(), src


def test_page_and_diagrams_are_served(client):
    assert client.get("").status_code == 200
    for f in ("app.js", "styles.css", "pages_intro.js", "pages_memory.js", "pages_copilot.js"):
        assert client.get(f).status_code == 200, f
    for d in ("big-picture.svg", "copilot-turn.svg", "extractor.svg"):
        assert client.get(f"diagrams/{d}").status_code == 200, d


def test_every_page_route_is_registered():
    js = "".join(p.read_text() for p in (APPBOOK / "frontend").glob("pages_*.js"))
    registered = set(re.findall(r'App\.page\("([^"]*)"', js))
    nav = set(
        re.findall(
            r'\["([a-z0-9-]*)", "[^"]+", "[^"]+"\]', (APPBOOK / "frontend/app.js").read_text()
        )
    )
    assert nav == registered, (nav, registered)
