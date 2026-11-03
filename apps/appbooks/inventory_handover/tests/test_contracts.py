"""Offline contracts: no database, no model.

Run from the appbook folder:  python -m pytest tests/test_contracts.py -q
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest

APPBOOK = Path(__file__).resolve().parents[1]
os.environ["DBPASSWORD"] = ""  # the runtime must fail fast and say why
os.environ["DB_DSN"] = "localhost:1/NOPE"

from backend import config  # noqa: E402
from backend.core import explorer  # noqa: E402
from backend.core.jobs import Job, JobManager  # noqa: E402
from backend.core.lab import LAB_ORDER, STEPS, Lab, _make_tracing_llm, _purpose  # noqa: E402
from backend.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        for _ in range(100):
            err = c.get("api/health").json().get("error") or ""
            if "Connecting" not in err:
                break
            time.sleep(0.05)
        yield c


def test_store_rules(monkeypatch):
    monkeypatch.setenv("APPBOOK_STORE", "ZH_INVENTORY")
    with pytest.raises(ValueError):
        config.load_settings()
    monkeypatch.setenv("APPBOOK_STORE", "bad store")
    with pytest.raises(ValueError):
        config.load_settings()
    monkeypatch.setenv("APPBOOK_STORE", "invapp")
    assert config.load_settings().store == "INVAPP"


def test_notebook_and_appbook_link_each_other():
    """The notebook sits in notebooks/agent_memory/inventory_handover/ and links to this appbook; the appbook links back."""
    notebook = (config.NOTEBOOK_DIR / config.NOTEBOOK_FILE).read_text()
    assert "apps/appbooks/inventory_handover" in notebook
    assert config.NOTEBOOK_URL.endswith(
        f"notebooks/agent_memory/inventory_handover/{config.NOTEBOOK_FILE}"
    )
    assert config.NOTEBOOK_URL in (APPBOOK / "frontend/app.js").read_text()
    assert config.NOTEBOOK_FILE in (APPBOOK / "README.md").read_text()


def test_defaults_match_the_notebook(monkeypatch):
    for k in ("DBUSER", "DB_DSN", "OCI_GENAI_MODEL", "ENDPOINT", "APPBOOK_STORE"):
        monkeypatch.delenv(k, raising=False)
    s = config.load_settings()
    assert (s.db_user, s.db_dsn, s.onnx_model, s.model) == (
        "prism",
        "localhost:1522/FREEPDB1",
        "ALL_MINILM_L12_V2",
        "xai.grok-4.3",
    )
    assert (
        s.endpoint == "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
        and s.region == "us-chicago-1"
    )


def test_oamp_version_and_overlay():
    """OAMP 26.8 from requirements.txt, or from the notebook's .packages overlay when it exists."""
    from importlib.metadata import version

    import oracleagentmemory
    from backend import _PACKAGES

    assert version("oracleagentmemory") == config.OAMP_VERSION
    assert _PACKAGES.parent == config.NOTEBOOK_DIR
    if _PACKAGES.is_dir():
        assert str(_PACKAGES) in oracleagentmemory.__file__


def test_step_graph_is_ordered_and_complete():
    seen = set()
    for key in LAB_ORDER:
        _, _, deps = STEPS[key]
        assert all(d in STEPS for d in deps), key
        assert all(d in seen for d in deps), f"{key} needs a step that comes later"
        seen.add(key)
        assert hasattr(Lab, f"step_{key}"), key


def test_tracing_llm_is_a_real_llm():
    """OAMP 26.8's background extraction fails with a wrapper; a subclass keeps its attributes."""
    from oracleagentmemory.core.llms import Llm

    cls = _make_tracing_llm(JobManager())
    assert issubclass(cls, Llm)


@pytest.mark.parametrize(
    "first,label",
    [
        ("You are a memory extraction module for an LLM agent.", "memory extraction"),
        (
            "You resolve links from newly extracted memories to stored candidate memories.",
            "link extraction",
        ),
        (
            "You maintain the persisted summary metadata for a thread. Return JSON only",
            "thread summary + topics",
        ),
        (
            "Given a user question and a document, determine whether the document should be keep",
            "pruning · keep or discard one document",
        ),
        ("Return a JSON object", "OAMP LLM call"),
    ],
)
def test_oamp_call_labels(first, label):
    assert _purpose([{"role": "system", "content": first}], None, None) == label
    assert _purpose("x", None, "handover draft") == "handover draft"


def test_jobs_count_events_and_bound_prompts():
    job = Job("t", "t")
    job.record_event("agent_memory", "agent_memory.search.started")
    job.record_event("agent_memory", "agent_memory.search.started")
    assert job.to_dict()["events"] == {"agent_memory · agent_memory.search.started": 2}
    job.record_llm("agent", "p", [{"role": "user", "content": "x" * 50_000}], "r", 1)
    assert len(job.llm_calls[0]["messages"][0]["content"]) < 21_000


def test_explorer_allowlist():
    lab = Lab(config.load_settings(), JobManager())
    allowed = explorer.allowlist(lab)
    assert all(t.startswith(lab.s.store + "_") for t in allowed)
    with pytest.raises(KeyError):
        explorer.rows(lab, "ZH_INVENTORY_MEMORY")
    with pytest.raises(KeyError):
        explorer.rows(lab, "USER_TABLES")
    assert "CONTENT" not in explorer.FILTER_COLUMNS


def test_approval_phrase_binds_draft_and_run():
    a = Lab.approval_phrase("draft one", "run1")
    assert a.startswith("APPROVE ") and len(a.split()[1]) == 64
    assert (
        a != Lab.approval_phrase("draft one.", "run1") != Lab.approval_phrase("draft one", "run2")
    )
    with pytest.raises(ValueError):
        Lab.approval_phrase("   ", "run1")


EXPECTED = {
    ("GET", "/api/health"),
    ("POST", "/api/reconnect"),
    ("GET", "/api/case"),
    ("GET", "/api/state"),
    ("POST", "/api/new-run"),
    ("POST", "/api/steps/{key}"),
    ("POST", "/api/run-all"),
    ("POST", "/api/approve"),
    ("GET", "/api/jobs"),
    ("GET", "/api/jobs/{job_id}"),
    ("GET", "/api/explorer/tables"),
    ("GET", "/api/explorer/rows"),
}


def test_routes():
    have = {(m.upper(), path) for path, ops in app.openapi()["paths"].items() for m in ops}
    assert EXPECTED <= have, EXPECTED - have


def test_health_explains_a_missing_password(client):
    h = client.get("api/health").json()
    assert h["ready"] is False and "DBPASSWORD" in h["error"]


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "api/state"),
        ("post", "api/steps/bare"),
        ("post", "api/run-all"),
        ("get", "api/explorer/tables"),
    ],
)
def test_live_routes_refuse_until_ready(client, method, path):
    r = getattr(client, method)(path)
    assert r.status_code == 503 and "DBPASSWORD" in r.json()["detail"]


def test_case_data_is_served_without_a_database(client):
    d = client.get("api/case").json()
    assert d["approved_quantity"] == 120 and d["approval_id"] == "PO-1048"


def test_bodies_are_bounded(client):
    assert client.post("api/approve", json={"phrase": "x" * 200}).status_code == 422


def test_frontend_is_relative_and_complete(client):
    index = (APPBOOK / "frontend/index.html").read_text()
    assert not re.search(r'(src|href)="/(?!/)', index)
    for src in re.findall(r'<script src="([^"]+)"', index):
        assert (APPBOOK / "frontend" / src).exists(), src
        assert client.get(src).status_code == 200, src
    js = "".join(p.read_text() for p in (APPBOOK / "frontend").glob("*.js"))
    assert not re.search(r"""['"`]/api/""", js)
    nav = set(
        re.findall(
            r'\["([a-z0-9-]*)", "[^"]+", "[^"]+"\]', (APPBOOK / "frontend/app.js").read_text()
        )
    )
    pages = set(re.findall(r'App\.page\("([^"]*)"', js))
    assert nav == pages, (nav, pages)
    for key in STEPS:  # every step's result has a renderer on some page
        assert re.search(rf"\b{key}: \(\s*d\s*\)", js), key
    for d in ("learning_stages.svg", "agent_loop.svg"):
        assert client.get(f"diagrams/{d}").status_code == 200
