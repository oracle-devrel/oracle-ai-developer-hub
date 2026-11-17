"""Live checks against a running appbook: real Oracle, real Grok on OCI.

    python tests/check_live.py [--base http://127.0.0.1:8735/]

Starts a new lab run, runs the whole lab, then approves the handover through
the review gate and cleans up. Hard checks mirror the notebook's own asserts;
what the model chose to say is reported as NOTE lines. About 25 Grok calls,
billed to the OCI tenancy; a few minutes.
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

FAILS: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + label + (f"  — {detail}" if detail else ""), flush=True)
    if not ok:
        FAILS.append(label)


def note(label: str, detail: str = "") -> None:
    print("NOTE " + label + (f"  — {detail}" if detail else ""), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8735/")
    c = httpx.Client(base_url=ap.parse_args().base.rstrip("/") + "/", timeout=60)

    def job(path, body=None, timeout=1200):
        started = c.post(path, json=body or {})
        started.raise_for_status()
        t0 = time.time()
        while True:
            j = c.get(f"api/jobs/{started.json()['id']}").json()
            if j["status"] in ("done", "error") or time.time() - t0 > timeout:
                break
            time.sleep(1)
        check(j["status"] == "done", f"job {path}", j.get("error") or f"{j['seconds']} s")
        return j

    h = c.get("api/health").json()
    if not h["ready"]:
        check(False, "runtime ready", h.get("error"))
        return 1
    check(
        h["versions"]["oracleagentmemory"] == "26.8.0" and h["store"] != "ZH_INVENTORY",
        "OAMP 26.8 and the appbook's own store",
        f"{h['store']} · {h['oci']['model']} · {h['oci']['region']}",
    )
    run = c.post("api/new-run").json()["run_id"]
    check(bool(run), "a new lab run", run)

    j = job("api/run-all")
    S = {s["key"]: s["data"] for s in j["steps"]}
    check(
        len(S) == 18 and all(s["status"] == "done" for s in j["steps"]),
        "all 18 lab steps ran",
        f"{len(S)} steps",
    )
    purposes = {x["purpose"] for x in j["llm_calls"]}
    check(
        {"memory extraction", "handover draft"} <= purposes
        and any(p.startswith("pruning") for p in purposes),
        "OAMP's own LLM calls are captured",
        ", ".join(sorted(purposes))[:200],
    )
    check(
        sum(j["events"].values()) > 100,
        "OAMP operation events are counted",
        f"{sum(j['events'].values())} events",
    )

    b = S["bare"]
    check("unknown" in b["fresh"].lower(), "Part 4: the bare model without notes answers unknown")
    note("Part 4 with notes", b["with_notes"].replace("\n", " "))
    t = S["transient"]
    check(
        t["with_notes"]["tool_called"] and t["fresh"]["tool_called"],
        "TODO 2: both agents called read_reorder_policy",
    )
    check(
        "unknown" in t["fresh"]["answer"].lower(),
        "Part 5: the fresh transient agent answers unknown",
    )
    check(
        S["connect"]["structured_ok"] and S["connect"]["embedding_shape"] == [1, 384],
        "TODO 3: structured output + (1, 384) embedding",
    )
    check(len(S["procedures"]["stored"]) == 4, "Part 6.3: four procedures read back from Oracle")
    check(S["threads"]["alice"] != S["threads"]["bob"], "TODO 4: separate planner labels")
    cap = S["capture"]
    check(
        cap["proposal_count"] >= 1 and cap["approval_count"] >= 1 and cap["case_ok"],
        "TODO 5: each ingestion persisted its own memories",
        f"{cap['proposal_count']} + {cap['approval_count']}",
    )
    note("inferred links", str(len(cap["inferred_links"])))
    ck = S["reviewed"]["checks"]
    check(
        all(ck.values()),
        "TODO 6–7: superseded history hidden from search, reachable by one hop",
        str(ck),
    )
    off = S["offload"]
    check(
        off["reference_chars"] < off["worksheet_chars"] and off["summary"].strip(),
        "TODO 9: reference smaller than the worksheet; summary present",
    )
    ma = S["memory_agent"]
    check(
        ma["recall_called"] and ma["stage_restored"] and ma["draft_restored"],
        "TODO 11: recall called; a new client restored stage and draft",
    )
    fr = S["fresh"]
    check(
        fr["recall_called"] and fr["current_fact_recalled"],
        "Part 7.3: a fresh session recalled the reviewed fact",
    )
    check(
        "120" in fr["answer"],
        "Part 7.3: the fresh memory aware answer has 120",
        fr["answer"].replace("\n", " ")[:120],
    )
    check(
        all(q["hit@3"] == 1 for q in S["retrieval"]["evaluation"]),
        "Part 8.1: each question's procedure in the top three",
    )
    check(
        S["pruning"]["pruned_hit@3"] == 1
        and len(S["pruning"]["pruned"]) <= len(S["pruning"]["unpruned"]),
        "TODO 12: pruning kept the expected procedure",
        f"{len(S['pruning']['unpruned'])} → {len(S['pruning']['pruned'])}",
    )
    check(len(S["observe"]["events"]) > 0, "TODO 13: events observed for one search")
    check(
        S["card"]["card"].startswith("<context_card>") and S["card"]["draft"].strip(),
        "TODO 14: card assembled and handover drafted",
        f"{S['card']['words']} words",
    )
    sc = S["scopes"]
    check(
        sc["bob_in_bob_scope"] and not sc["bob_in_mug_scope"] and sc["alice_client_can_select_bob"],
        "TODO 15: filters select, they don't authorize",
    )
    rv = S["review"]
    check(rv["unapproved_write_blocked"], "TODO 16: an unapproved write is blocked")
    bad = c.post("api/approve", json={"phrase": "APPROVE 0000"})
    check(bad.status_code == 403, "a wrong phrase is refused")
    good = c.post("api/approve", json={"phrase": rv["phrase"]})
    check(
        good.status_code == 200 and good.json()["receipt_id"] == f"handover-{run}",
        "the exact phrase saves the reviewed draft",
        good.text[:80],
    )
    check(all(S["procedure"]["checks"].values()), "TODO 17: lesson recalled; no case IDs leaked")
    check(
        S["ttl"]["search_hits"] == 0 and S["ttl"]["row_count"] == 1,
        "Part 9.4: expired = hidden, not erased",
    )

    rows = c.get(
        "api/explorer/rows", params={"table": h["store"] + "_RECORD_CHUNKS", "limit": 5}
    ).json()
    check(
        all(r.get("embedding", "").startswith("VECTOR(") for r in rows["rows"]),
        "the explorer never sends vectors",
    )
    check(
        c.get("api/explorer/rows", params={"table": "ZH_INVENTORY_MEMORY"}).status_code == 404,
        "the explorer refuses the notebook's store",
    )

    j = job("api/steps/cleanup")
    cl = next(s for s in j["steps"] if s["key"] == "cleanup")["data"]
    check(cl["all_zero"], "Part 9.5: both case threads now have zero rows", str(cl["after"]))
    check(
        cl["shared_procedures_kept"] >= 4,
        "shared procedures are kept",
        str(cl["shared_procedures_kept"]),
    )
    blocked = c.post("api/steps/bare")
    jid = blocked.json()["id"]
    time.sleep(1.5)
    check(
        c.get(f"api/jobs/{jid}").json()["status"] == "error",
        "a cleaned-up run refuses more steps until a new run starts",
    )

    print(f"\n{'ALL PASSED' if not FAILS else str(len(FAILS)) + ' FAILED: ' + '; '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
