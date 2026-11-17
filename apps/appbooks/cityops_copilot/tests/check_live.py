"""Live checks against a running appbook: real Oracle, real Ollama.

    python tests/check_live.py [--base http://127.0.0.1:8730/]

It resets the appbook's workspace first (CITYAPP_* only), then walks every
Part and the handoff story. Hard checks mirror the notebook's own assertions
and fail the run; extraction is probabilistic, so what the model chose to
extract is reported as an observation, not a failure. Takes several minutes
on a local model.
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

FAILS: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    print(("PASS " if ok else "FAIL ") + label + (f"  — {detail}" if detail else ""), flush=True)
    if not ok:
        FAILS.append(label)
    return ok


def observe(label: str, detail: str = "") -> None:
    print("NOTE " + label + (f"  — {detail}" if detail else ""), flush=True)


class Client:
    def __init__(self, base: str):
        self.http = httpx.Client(base_url=base.rstrip("/") + "/", timeout=120)

    def get(self, path, **params):
        r = self.http.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()

    def post(self, path, body=None, expect=200):
        r = self.http.post(path, json=body or {})
        if r.status_code != expect:
            raise AssertionError(f"POST {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()

    def job(self, path, body=None, timeout=1200):
        started = self.post(path, body)
        t0 = time.time()
        while True:
            j = self.get(f"api/jobs/{started['id']}")
            if j["status"] in ("done", "error"):
                break
            if time.time() - t0 > timeout:
                raise TimeoutError(f"{path} still {j['status']} after {timeout}s")
            time.sleep(1.0)
        check(j["status"] == "done", f"job {path} finished", j.get("error") or f"{j['seconds']} s")
        return j


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8730/")
    args = ap.parse_args()
    c = Client(args.base)

    h = c.get("api/health")
    if not check(
        h["ready"],
        "runtime ready",
        h.get("error") or f"{h['db']['user']}@{h['db']['dsn']} · {h['ollama']['model']}",
    ):
        return 1
    prefix = h["prefix"]
    check(
        prefix != "CITY_" and h["onnx"]["ok"] and h["ollama"]["ok"],
        "prefix, ONNX model and Ollama model",
        prefix,
    )

    # ------------------------------------------------------------ Part 1
    j = c.job("api/reset")
    o = c.get("api/overview")
    t = lambda n: o["tables"].get(prefix + n, -1)  # noqa: E731
    check(
        t("ASSET") == 26 and t("INSPECTION_FINDING") == 15,
        "reset reloads 26 assets and the first 15 findings",
        f"{t('ASSET')} assets, {t('INSPECTION_FINDING')} findings",
    )
    check(t("MEMORY") == 0 and t("MESSAGE") == 0, "reset leaves memory empty")
    check(
        all(not k.startswith("CITY_") for k in o["tables"]), "only the appbook's tables are counted"
    )
    check(o["hnsw"], "HNSW index on the findings")

    # ------------------------------------------------------------ Part 2
    e = c.post(
        "api/embed",
        {
            "texts": [
                "corrosion on bearing assembly",
                "rust on the pier bearings",
                "the substation transformer hums loudly",
            ]
        },
    )
    check(
        e["shape"] == [3, 384] and e["dtype"] == "float32",
        "TODO 1: in-database embeddings are (n, 384) float32",
    )
    d = e["distances"]
    check(
        d[0][1] < d[0][2] and d[0][1] < d[1][2],
        "the two corrosion sentences are closest",
        f"A-B {d[0][1]:.3f}, A-C {d[0][2]:.3f}, B-C {d[1][2]:.3f}",
    )

    # ------------------------------------------------------------ Part 3
    check(len(c.get("api/assets")["assets"]) == 26, "26 assets in the registry")
    narr = c.get("api/narratives", asset="Harbor Bridge", limit=5)
    check(
        narr["total"] > 0 and len(narr["sample"]) == 4,
        "Harbor Bridge narratives and the notebook's sample of 4",
    )
    j = c.job(
        "api/report-event",
        {
            "asset_id": "Harbor Bridge",
            "inspector": "smoke_inspector",
            "narrative": narr["narratives"][0]["narrative"],
            "thread_id": "smoke_thread",
        },
    )
    r = j["result"]
    check(
        len(r["message_ids"]) >= 1 and len(r["messages"]) == 1,
        "TODO 2: add_messages stores the narrative verbatim",
    )
    check(
        r["messages"][0]["content"].startswith(
            "[Asset: Harbor Bridge] [Inspector: smoke_inspector]"
        ),
        "the message names the asset and inspector",
    )
    extraction = [x for x in j["llm_calls"] if x["purpose"] == "memory extraction"]
    check(
        len(extraction) == 1 and extraction[0]["who"] == "sdk",
        "one SDK extraction call is captured, with its prompt",
        f"{extraction[0]['ms']} ms" if extraction else "",
    )
    observe(
        "smoke narrative extracted", ", ".join(m["memory_type"] for m in r["memories"]) or "nothing"
    )

    j = c.job("api/extraction-demo", {"count": 4})
    check(
        len(j["steps"]) == 4 and all(s["status"] == "done" for s in j["steps"]),
        "four narratives reported",
    )
    s = c.post(
        "api/search",
        {
            "query": "recurring asset concerns and inspector practices",
            "user_id": "inspector_demo",
            "agent_id": "CITY",
            "record_types": ["fact", "preference", "guideline", "memory"],
            "max_results": 50,
        },
    )
    check(
        len(s["results"]) >= 3,
        "TODO 3: at least 3 records extracted from 4 narratives",
        f"{len(s['results'])} records",
    )
    observe("record types extracted", ", ".join(sorted({x["record_type"] for x in s["results"]})))
    none = c.post(
        "api/search",
        {
            "query": "recurring asset concerns and inspector practices",
            "user_id": None,
            "agent_id": "CITY",
            "record_types": ["fact", "preference", "guideline", "memory"],
        },
    )
    check(
        not any(x["user_id"] == "inspector_demo" for x in none["results"]),
        "user_id=None does not see inspector_demo's records",
        f"{len(none['results'])} unscoped hits",
    )
    mem = c.get("api/memories", thread_id="inspect_demo", limit=100)["memories"]
    check(
        len(mem) >= 3
        and all(m["memory_type"] in ("fact", "preference", "guideline", "memory") for m in mem),
        "the memory log holds only the four native record types",
    )

    # ------------------------------------------------------------ Part 4
    q = "bearing corrosion at piers"
    broad = c.post("api/findings/search", {"description": q, "k": 5})["rows"]
    bridge = c.post("api/findings/search", {"description": q, "asset_id": "Harbor Bridge", "k": 5})[
        "rows"
    ]
    corr = c.post("api/findings/search", {"description": q, "category": "corrosion", "k": 5})[
        "rows"
    ]
    check(len(broad) >= 3, "TODO 5: broad search returns at least 3 findings", str(len(broad)))
    check(
        bridge and all(x["asset_id"] == "Harbor Bridge" for x in bridge),
        "TODO 5: asset filter holds",
    )
    check(corr and all(x["category"] == "corrosion" for x in corr), "TODO 5: category filter holds")
    check(
        all(a["score"] <= b["score"] for a, b in zip(bridge, bridge[1:], strict=False)),
        "results are ordered by distance",
    )
    fid = c.post(
        "api/findings/log",
        {
            "asset_id": "Harbor Bridge",
            "inspector": "checkpoint_test",
            "category": "corrosion",
            "severity": "medium",
            "overall_grade": "C",
            "days_ago": 0,
            "description": "Surface corrosion on pier 2 bearing assemblies; ~25% section loss observed.",
            "recommendation": "Remove corrosion, apply primer + finish coat within 60 days.",
        },
    )["finding_id"]
    rows = c.get(
        "api/explorer/rows",
        table=prefix + "INSPECTION_FINDING",
        filter_column="inspector",
        filter_value="checkpoint_test",
    )
    check(
        rows["total"] == 1 and rows["rows"][0]["finding_id"] == fid,
        "TODO 4: log_finding writes one retrievable row",
    )
    check(rows["rows"][0]["embedding"] == "VECTOR(384)", "the Data Explorer never sends vectors")
    r = c.http.post(
        "api/findings/log",
        json={
            "asset_id": "Atlantis Bridge",
            "inspector": "x",
            "category": "corrosion",
            "severity": "low",
            "description": "nothing here",
        },
    )
    check(r.status_code == 422, "log_finding refuses an asset that is not in the registry")
    j = c.job("api/findings/load-all")
    total = c.get("api/findings")["total"]
    check(
        total == 223, "load-all brings every dataset finding (222 + the checkpoint one)", str(total)
    )

    # ------------------------------------------------------------ Part 5
    j = c.job("api/scoping-demo")
    check(j["result"]["checks"]["no_leak"], "Part 5: Vance cannot see Mercer's personal note")
    check(j["result"]["checks"]["city_visible"], "Part 5: Vance can see the city-wide guideline")
    check(
        any("shift" in (x["content"] or "").lower() for x in j["result"]["mercer"]["results"]),
        "Mercer can see her own note",
    )
    before = c.get("api/overview")["tables"][prefix + "MEMORY"]
    j2 = c.job("api/scoping-demo")
    after = c.get("api/overview")["tables"][prefix + "MEMORY"]
    check(
        before == after and j2["result"]["checks"]["no_leak"],
        "the scoping demo can be re-run without duplicating its notes",
        f"{before} → {after} memory rows",
    )

    # -------------------------------------------------- Part 6 + handoff
    j = c.job("api/handoff/mercer-day1")
    check(
        all(s["status"] == "done" for s in j["steps"]), "Mercer's copilot turn: all nine steps done"
    )
    purposes = [x["purpose"] for x in j["llm_calls"]]
    check(
        "copilot answer" in purposes and "memory extraction" in purposes,
        "the turn's model calls are captured",
        ", ".join(purposes),
    )
    card = next(s for s in j["steps"] if s["key"] == "card")["data"]["xml"]
    check(
        card == "",
        "a brand-new thread has an empty context card (nothing to summarise yet)",
        f"{len(card)} chars",
    )
    prompt = next(s for s in j["steps"] if s["key"] == "prompt")["data"]["user"]
    check(
        all(
            h in prompt
            for h in (
                "# Current inspection narrative",
                "# Asset record",
                "# Thread context",
                "# Relevant memory from prior inspections",
                "# Similar past findings",
            )
        ),
        "the prompt has the notebook's five sections",
    )
    check(
        j["result"]["thread_id"] == "Harbor Bridge::Evelyn_H_Mercer",
        "Mercer's private thread is <asset>::<inspector>",
    )
    check(
        len(j["result"]["answer"]) > 40,
        "the copilot answered",
        f"{len(j['result']['answer'])} chars",
    )
    c.job("api/handoff/mercer-log")
    j = c.job("api/handoff/mercer-followup")
    card = next(s for s in j["steps"] if s["key"] == "card")["data"]["xml"]
    check(
        card.startswith("<context_card>") and "<recent_messages>" in card and "<summary>" in card,
        "on her second turn the context card is XML with its blocks",
        f"{len(card)} chars",
    )
    check(
        "Pier 2" in card.split("<recent_messages>")[-1], "the card carries her first turn verbatim"
    )
    pooled_hb = c.get("api/memories", user_id="Harbor Bridge", limit=100)["memories"]
    check(
        len(pooled_hb) >= 1 and all(m["user_id"] == "Harbor Bridge" for m in pooled_hb),
        "Mercer's records are filed under the asset",
        f"{len(pooled_hb)} records",
    )
    observe(
        "guideline extracted from Mercer's turns",
        str(sum(m["memory_type"] == "guideline" for m in pooled_hb)),
    )
    j = c.job("api/handoff/vance")
    v = j["result"]
    check(v["thread_id"] == "Harbor Bridge::Jordan_Vance", "Vance gets his own thread")
    check(
        any(x["inspector"] == "Evelyn_H_Mercer" for x in v["similar"]),
        "Vance's similar findings include Mercer's logged finding",
    )
    vcard = next(s for s in j["steps"] if s["key"] == "card")["data"]["xml"]
    recent = (
        vcard.split("<recent_messages>")[-1].split("</recent_messages>")[0]
        if "<recent_messages>" in vcard
        else ""
    )
    check("Evelyn_H_Mercer @" not in recent, "Vance's context card holds none of Mercer's messages")
    relevant = (
        vcard.split("<relevant_information>")[-1].split("</relevant_information>")[0]
        if "<relevant_information>" in vcard
        else ""
    )
    observe(
        "Vance's card relevant_information mentions Mercer",
        str("Mercer" in relevant or "Evelyn" in relevant),
    )
    from_mercer = [x for x in v["pooled"] if (x["thread_id"] or "").endswith("::Evelyn_H_Mercer")]
    observe(
        "pooled records in Vance's prompt that came from Mercer's thread",
        f"{len(from_mercer)} of {len(v['pooled'])}",
    )
    j = c.job("api/handoff/compare")
    check(
        len(j["result"]["answer"]) > 40 and j["result"]["with_memory"] == v["answer"],
        "the stateless comparison ran",
    )
    hs = c.get("api/handoff")
    check(
        all(
            hs["steps"][k]
            for k in ("mercer-day1", "mercer-log", "mercer-followup", "vance", "compare")
        ),
        "the story state is kept",
    )

    # ------------------------------------------------------- explorer
    tables = c.get("api/explorer/tables")["tables"]
    check(
        {x["short"] for x in tables}
        >= {"ASSET", "INSPECTION_FINDING", "THREAD", "MESSAGE", "MEMORY"},
        "the explorer lists the tables",
    )
    r = c.http.get("api/explorer/rows", params={"table": "CITY_MEMORY"})
    check(r.status_code == 404, "the explorer refuses the notebook's tables")
    r = c.http.get(
        "api/explorer/rows",
        params={"table": prefix + "MEMORY", "filter_column": "content", "filter_value": "x"},
    )
    check(r.status_code == 404, "the explorer refuses filters on non-id columns")
    msgs = c.get("api/explorer/rows", table=prefix + "MESSAGE", limit=200)
    check(
        all(len(str(x.get("content") or "")) <= 300 for x in msgs["rows"]),
        "explorer text is cut to 300 characters",
    )

    print(f"\n{'ALL PASSED' if not FAILS else str(len(FAILS)) + ' FAILED: ' + '; '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
