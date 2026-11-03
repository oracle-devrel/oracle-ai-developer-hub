/* Part 6 (the copilot end to end), the handoff story, memory types and takeaways. Diagram-first. */

(() => {
  const { C, esc, api, $, $$, trunc } = App;
  const F = D.F;
  const MERCER = "Evelyn_H_Mercer",
    VANCE = "Jordan_Vance";

  /* ---------------------------------------- renderers for call_copilot's steps */

  const SECTION_COLORS = {
    narrative: "var(--d-req)",
    asset: "var(--d-data)",
    card: "var(--d-memory)",
    pooled: "var(--d-read)",
    similar: "var(--c-domain)",
  };
  const SECTION_LABELS = {
    narrative: "narrative — what the inspector typed",
    asset: "asset record (step 2)",
    card: "context card — this thread (step 3)",
    pooled: "pooled memory — other inspectors (step 4b)",
    similar: "similar findings (step 4)",
  };
  const fromWho = (thread) => (thread && thread.includes("::") ? thread.split("::")[1] : null);

  function anatomy(sections) {
    const entries = Object.entries(sections);
    const total = entries.reduce((a, [, v]) => a + Math.max(v.length, 1), 0);
    return `<div class="anatomy">${entries.map(([k, v]) => `<span style="flex:${Math.max(v.length, 1) / total};background:${SECTION_COLORS[k]}" title="${esc(SECTION_LABELS[k])}: ${v.length} chars"></span>`).join("")}</div>
      <div class="anatomy-legend">${entries.map(([k, v]) => `<span><i style="background:${SECTION_COLORS[k]}"></i>${esc(SECTION_LABELS[k])} · ${v.length}</span>`).join("")}</div>`;
  }

  Object.assign(App.STEP_RENDER, {
    thread: (
      d
    ) => `<p class="small">Thread <span class="mono">${esc(d.thread_id)}</span> — ${d.created ? "created now" : "already existed"}.
      Scope: <span class="mono">user_id=${esc(d.user_id)}</span> (the asset), <span class="mono">agent_id=${esc(d.agent_id)}</span>.</p>`,
    asset: (d) =>
      `${d.asset ? C.json(d.asset) : C.empty("No asset record.")}${C.code(d.sql, "sql")}`,
    card: (d) =>
      d.xml
        ? `<p class="small muted">The SDK's prompt-ready view of <b>this inspector's own thread</b> — ${d.chars} characters, passed to the agent verbatim.</p>${C.code(d.xml, "xml", { wrap: true })}`
        : `<p class="small">The card is <b>empty</b>: first turn on a new thread, nothing to summarise yet. On this turn everything about the asset's past comes from steps 4 and 4b.</p>`,
    similar: (d) =>
      `${C.findingCards(d.rows, { highlightInspector: MERCER })}${C.more("The SQL", C.code(d.sql, "sql") + C.json(d.binds))}`,
    pooled: (d) => `${C.code(
      `memory.search_async(query=narrative, ${Object.entries(d.call)
        .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
        .join(", ")})`,
      "python",
      { wrap: true }
    )}
      ${C.records(d.results, (r) => ({ max: 400, extra: fromWho(r.thread_id) ? C.chip("model", "from " + fromWho(r.thread_id) + "'s thread") : "", empty: "No pooled memory for this asset yet — it fills up as inspectors use the copilot." }))}`,
    prompt: (
      d
    ) => `${anatomy(d.sections)}<div class="prompt-section" style="--c:var(--text-3)"><div class="lbl">system prompt</div><pre>${esc(d.system)}</pre></div>
      ${Object.entries(d.sections)
        .map(
          ([k, v]) =>
            `<div class="prompt-section" style="--c:${SECTION_COLORS[k]}"><div class="lbl">${esc(SECTION_LABELS[k])} · ${v.length} chars</div><pre>${esc(v)}</pre></div>`
        )
        .join("")}`,
    answer: (d) => `<div class="answer">${esc(d.answer)}</div>`,
    persist: (d) =>
      `<p class="small muted">Both messages stored verbatim; the extractor ran inside the same call (step 8).</p>${C.records(d.messages, { max: 500 })}`,
    learned: (
      d
    ) => `${C.records(d.memories, { empty: "The extractor found nothing new worth keeping this turn." })}
      <div class="deltas">${Object.entries(d.deltas || {})
        .map(([t, n]) => C.chip("memory", `${t} +${n}`))
        .join("")}</div>`,
  });

  /* ================================================================ Part 6 */

  App.page("part6", {
    accent: "var(--c-model)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 6 · The CityOps Copilot, end to end</p>
        <h1>One turn: read both layers, reason, write back</h1>
        <p class="lede">Every component from Parts 3–5 snaps into one function, <span class="mono">call_copilot</span>.</p>
        ${C.learn([
          ["See", "the eight steps of a turn"],
          ["Read", "the context card and the exact prompt"],
          ["Try", "a live turn that lights up step by step"],
        ])}

        <h2>The eight steps</h2>
        ${C.fig(
          F.turnMap(),
          `Five reads build one prompt: the thread, the asset record, this inspector's context card, the most similar findings and the
          asset's pooled memory. Then one answer, and the write-back — which feeds the next turn's card and pooled search.`
        )}
        <div class="grid2">
          <div class="card state-card k-domain"><div class="kicker">step 4 · structured evidence</div>
            <p class="small muted" style="margin:6px 0 0">A prior finding's category, severity, grade and recommendation, by vector SQL.</p></div>
          <div class="card state-card k-memory"><div class="kicker">step 4b · operating knowledge</div>
            <p class="small muted" style="margin:6px 0 0">Facts and guidelines other inspectors left on this asset — the bridge between inspectors.</p></div>
        </div>

        ${C.tryPanel(
          "p6-try",
          "Run a copilot turn",
          "call_copilot() · 3 model calls, about half a minute to two minutes",
          `
          <div class="form">
            <div class="row">
              <label>inspector<input type="text" data-insp list="p6-inspectors" value="${VANCE}"><datalist id="p6-inspectors"><option value="${MERCER}"><option value="${VANCE}"></datalist></label>
              <label>asset<select data-asset></select></label>
            </div>
            <label>narrative<textarea data-narr rows="3">Reviewing Harbor Bridge as part of routine cycle. Noticing rust bleed near a pier on the south side and what looks like spalling on the concrete pedestal below.</textarea></label>
            <div class="row"><button class="btn primary" data-go>Run call_copilot</button>
              <span class="small faint">Watch the map; open any step below for its data.</span></div>
          </div>
          <div id="p6-map" hidden></div><div id="p6-anatomy"></div><div id="p6-job"></div>`
        )}

        ${C.more(
          "What's in the context card",
          C.code(
            `<context_card>
  <topics>               short retrieval topics (SDK LLM)       </topics>
  <summary>              rolling summary, ≤ 3 sentences          </summary>
  <relevant_information> records relevant to this thread         </relevant_information>
  <recent_messages>      the latest messages, verbatim           </recent_messages>
</context_card>`,
            "xml"
          ) +
            `<p class="small muted">One small SDK LLM call per turn keeps it fresh. On an inspector's first turn at an asset the card is empty — it is built before the turn is saved.</p>`
        )}
        ${C.more("See the whole call_copilot", C.code(COPILOT_CODE))}
        ${C.takeaway(`<p>A memory-aware turn reads the system of record and memory, answers, then writes back — so the next turn starts better informed.</p>`)}`;
      if (!ctx.ready) {
        $("#p6-job", el).innerHTML = ctx.notReady();
        return;
      }
      api.get("assets").then(({ assets }) => {
        $("[data-asset]", el).innerHTML = assets
          .map(
            (a) =>
              `<option ${a.asset_id === "Harbor Bridge" ? "selected" : ""}>${esc(a.asset_id)}</option>`
          )
          .join("");
      });
      $("[data-go]", el).onclick = () => {
        const map = $("#p6-map", el);
        map.innerHTML = F.turnMap();
        map.hidden = false;
        $("#p6-anatomy", el).innerHTML = "";
        App.runJob(
          api.post("copilot", {
            narrative: $("[data-narr]", el).value.trim(),
            inspector_id: $("[data-insp]", el).value.trim(),
            asset_id: $("[data-asset]", el).value,
          }),
          $("#p6-job", el),
          {
            autoOpen: ["answer", "learned"],
            onUpdate: (job) => F.turnMapUpdate(map, job),
            onDone: (job) => {
              const ms = (k) => (job.steps.find((s) => s.key === k) || {}).ms || 0;
              const memory = ms("card") + ms("persist"),
                answer = ms("answer");
              const p = job.steps.find((s) => s.key === "prompt");
              $("#p6-anatomy", el).innerHTML =
                C.watch(`<p>Memory work — the context card (${App.fmtMs(ms("card"))}) and storing + extracting (${App.fmtMs(ms("persist"))}) — took
                <b>${App.fmtMs(memory)}</b>; the answer itself took <b>${App.fmtMs(answer)}</b>. ${
                  memory > answer
                    ? "Here the memory layer's own LLM calls cost more time than the reply — worth knowing when you size a model for the SDK."
                    : "Here the reply took longer than the memory layer's own LLM calls."
                }</p>`) +
                (p && p.data
                  ? `<h3>Anatomy of the prompt this turn sent</h3>${anatomy(p.data.sections)}`
                  : "");
            },
          }
        );
      };
    },
  });

  const COPILOT_CODE = `async def call_copilot(narrative: str, inspector_id: str, asset_id: str) -> str:
    # 1. Resolve this inspector's PRIVATE per-asset thread (get-or-create).
    thread_id = f"{asset_id}::{inspector_id}"
    try:
        t = memory.get_thread(thread_id)
    except Exception:
        t = None
    if t is None:
        t = memory.create_thread(user_id=asset_id, thread_id=thread_id, agent_id="CITY",
                                 enable_context_summary=True, context_summary_update_frequency=2)
    asset = get_asset(asset_id)                                                   # 2. asset record
    card = await t.get_context_card_async(fallback_message_count=100,
                                          max_recent_messages=10, max_relevant_results=8)  # 3. context card
    similar = find_similar_findings(narrative, asset_id=asset_id, k=3)           # 4. similar findings
    pooled = await memory.search_async(query=narrative, user_id=asset_id, agent_id="CITY",
                                       exact_thread_match=False,
                                       record_types=["fact", "guideline", "memory"], max_results=3)  # 4b
    context = (...)                                                              # 5. five sections
    answer = (await call_ollama_chat([{"role": "system", "content": COPILOT_SYSTEM_PROMPT},
                                      {"role": "user", "content": context}])).choices[0].message.content
    await t.add_messages_async([                                                 # 7–8. persist + extract
        Message(role="user", content=f"[{inspector_id} @ {asset_id}] {narrative}"),
        Message(role="assistant", content=answer),
    ])
    return answer`;

  /* ================================================================ handoff */

  const STORY = [
    {
      key: "mercer-day1",
      who: "mercer",
      when: "Day 1",
      title: "Mercer asks the copilot about Pier 2",
      fn: "call_copilot",
      cost: "3 model calls",
    },
    {
      key: "mercer-log",
      who: "mercer",
      when: "Day 1",
      title: "Mercer records the formal finding",
      fn: "log_finding",
      cost: "no model",
    },
    {
      key: "mercer-followup",
      who: "mercer",
      when: "Day 1, afternoon",
      title: "Mercer adds a coordination note",
      fn: "call_copilot",
      cost: "3 model calls",
    },
    {
      key: "vance",
      who: "vance",
      when: "Day N",
      title: "Vance — who never met Mercer — reports something similar",
      fn: "call_copilot",
      cost: "3 model calls",
    },
    {
      key: "compare",
      who: "vance",
      when: "Compare",
      title: "The same question with no memory at all",
      fn: "LLM only",
      cost: "1 model call",
    },
  ];

  App.page("handoff", {
    accent: "var(--c-model)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">See it work · the cross-inspector handoff</p>
        <h1>Vance inherits Mercer's work — with no handoff meeting</h1>
        <p class="lede">One inspector's finding and practical advice reach a second inspector at the same bridge days later, while each inspector's raw conversation stays private.</p>
        <div id="handoff-fig">${F.handoff()}</div>
        <p class="fig-cap">Two routes, both automatic: her <b>finding</b> arrives by vector search over the system of record (step 4); her <b>lessons</b> arrive through the
          asset-pooled memory (step 4b). The diagram fills in with what actually happened once Vance's step has run.</p>
        <div class="row" style="margin:18px 0 4px"><button class="btn primary" data-all>Run the whole story</button>
          <span class="small faint">Five steps in order — about 3–6 minutes on a local model. Or run them one by one.</span></div>
        <div class="timeline" id="story"></div>

        <h2>Where did Vance's context come from?</h2>
        <div id="provenance">${C.empty("Run Vance's step to see which parts of his prompt came from Mercer.")}</div>
        <h2>With and without memory</h2>
        <div id="compare">${C.empty("Run the last two steps to compare the answers side by side.")}</div>
        ${C.takeaway(`<p>The read path consumes exactly what an earlier write path produced — that is the whole point of agent memory.</p>`)}`;
      if (!ctx.ready) {
        $("#story", el).innerHTML = ctx.notReady();
        return;
      }
      loadStory(el);
    },
  });

  async function loadStory(el) {
    let state;
    try {
      state = await api.get("handoff");
    } catch (e) {
      $("#story", el).innerHTML = C.error(e);
      return;
    }
    const story = $("#story", el);
    story.innerHTML = STORY.map((s, i) => {
      const narrative = state.narratives[s.key];
      const done = !!state.steps[s.key];
      return `<div class="tl-item ${done ? "done" : ""}" data-step="${s.key}"><div class="tl-mark">${done ? "✓" : i + 1}</div>
        <div class="tl-card"><div class="who"><span class="avatar ${s.who}">${s.who === "mercer" ? "EM" : "JV"}</span>${esc(s.when)} · <span class="mono">${esc(s.fn)}</span> · ${esc(s.cost)}</div>
          <h3 style="margin-top:6px">${esc(s.title)}</h3>
          ${narrative ? C.more("The narrative", `<div class="answer plain small">${esc(narrative)}</div>`) : ""}
          ${s.key === "mercer-log" ? C.more("The finding", C.json(state.finding)) : ""}
          <div class="row" style="margin-top:10px"><button class="btn ${done ? "" : "primary"} small" data-run="${s.key}">${done ? "Run again" : "Run this step"}</button>
          ${s.key === "mercer-followup" ? `<button class="btn small" data-check>Did Mercer's turns leave a guideline?</button>` : ""}</div>
          <div class="step-out" data-out="${s.key}">${done ? summary(s.key, state.steps[s.key]) : ""}</div>
          ${s.key === "mercer-followup" ? `<div data-check-out></div>` : ""}</div></div>`;
    }).join("");
    const results = { ...state.steps };
    renderAfter(el, results);

    const runStep = (key) =>
      new Promise((resolve) => {
        const out = $(`[data-out="${key}"]`, story);
        const box = document.createElement("div");
        out.innerHTML = "";
        out.appendChild(box);
        App.runJob(api.post("handoff/" + key), box, {
          autoOpen: ["answer"],
          onDone: (job) => {
            results[key] = job.result;
            const item = $(`[data-step="${key}"]`, story);
            item.classList.add("done");
            $(".tl-mark", item).textContent = "✓";
            renderAfter(el, results);
            resolve(true);
          },
          onError: () => resolve(false),
        });
      });
    $$("[data-run]", story).forEach((b) => (b.onclick = () => runStep(b.dataset.run)));
    $("[data-all]", el).onclick = async (ev) => {
      ev.target.disabled = true;
      for (const s of STORY) {
        $(`[data-step="${s.key}"]`, story).scrollIntoView({ behavior: "smooth", block: "start" });
        if (!(await runStep(s.key))) break;
      }
      ev.target.disabled = false;
    };
    $("[data-check]", story).onclick = async () => {
      const out = $("[data-check-out]", story);
      try {
        const r = await api.get("memories", { user_id: "Harbor Bridge", limit: 40 });
        const g = r.memories.filter((m) => m.memory_type === "guideline");
        out.innerHTML = `<p class="small" style="margin-top:10px">${r.memories.length} record(s) under <span class="mono">user_id="Harbor Bridge"</span>; ${g.length} guideline(s).
          ${g.length ? "" : "Extraction is probabilistic — if the guidance landed as a fact, run Mercer's Day-1 step again."}</p>
          ${C.records(r.memories, (m) => ({ max: 300, highlight: m.memory_type === "guideline", extra: fromWho(m.thread_id) ? `<span>from ${esc(fromWho(m.thread_id))}</span>` : "" }))}`;
      } catch (e) {
        out.innerHTML = C.error(e);
      }
    };
  }

  function summary(key, r) {
    if (!r) return "";
    if (key === "mercer-log")
      return `<p class="small" style="margin-top:10px">${C.chip("ok", "logged")} finding <span class="mono">${esc(r.finding_id)}</span></p>`;
    return r.answer
      ? `<div class="msg-role" style="margin-top:10px">copilot</div><div class="answer">${esc(r.answer)}</div>`
      : "";
  }

  function renderAfter(el, results) {
    const v = results.vance;
    if (v && (v.pooled || v.similar)) {
      F.handoffUpdate($("#handoff-fig", el), v);
      const pooledFromMercer = (v.pooled || []).filter((r) => fromWho(r.thread_id) === MERCER);
      const findingFromMercer = (v.similar || []).filter((r) => r.inspector === MERCER);
      $("#provenance", el).innerHTML = `
        <div class="grid2">
          <div class="card state-card k-domain"><div class="kicker">step 4 · similar findings</div>
            <h3>${findingFromMercer.length ? "Mercer's logged finding reached Vance" : "No finding of Mercer's in Vance's top 3"}</h3>
            ${C.findingCards(v.similar || [], { highlightInspector: MERCER })}</div>
          <div class="card state-card k-memory"><div class="kicker">step 4b · asset-pooled memory</div>
            <h3>${pooledFromMercer.length ? `${pooledFromMercer.length} record(s) distilled from Mercer's thread` : "No record from Mercer's thread in Vance's top 3"}</h3>
            ${C.records(v.pooled || [], (r) => ({ max: 300, highlight: fromWho(r.thread_id) === MERCER, extra: fromWho(r.thread_id) ? `<span>from ${esc(fromWho(r.thread_id))}'s thread</span>` : "", empty: "Nothing pooled yet." }))}</div>
        </div>
        ${C.watch(`<p>Vance's context card holds only <b>his own</b> thread. Everything highlighted crossed over through the asset — and none of Mercer's raw messages did.</p>`)}`;
    }
    const c = results.compare,
      withMem = (results.vance && results.vance.answer) || (c && c.with_memory);
    if (c && c.answer) {
      $("#compare", el).innerHTML = `<div class="compare">
        <div><h3>${C.chip("", "without memory")} stateless LLM</h3><div class="answer plain">${esc(c.answer)}</div>
          <p class="small faint" style="margin-top:6px">It can't know Pier 2, Mercer's grade or the 60-day plan. Watch for <b>invented history</b>: with nothing to retrieve, a small model may make up prior findings or guideline numbers.</p></div>
        <div><h3>${C.chip("memory", "with memory")} the copilot</h3>${withMem ? `<div class="answer">${esc(withMem)}</div>` : C.empty("Run Vance's step first.")}
          <p class="small faint" style="margin-top:6px">Look for the prior grade, the recommendation timeline, and guidance that came from Mercer.</p></div></div>`;
    }
  }

  /* ================================================================ memory types */

  App.page("memory-types", {
    accent: "var(--c-ok)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Wrap up · memory types and takeaways</p>
        <h1>What you actually built</h1>
        <p class="lede">One copilot covers most of the standard agent-memory picture. Here is the map back.</p>
        <div id="mt-live"></div>
        ${C.fig(
          F.memoryMap(),
          `The SDK's four record types are the cognitive memory types; threads, messages, summaries and the context card cover the rest.
          <span class="mono">oracleagentmemory</span> is the governed memory core — what the agent <b>knows, said, learned and shares</b>.`
        )}

        <h2>What each layer earned</h2>
        <div class="grid3">
          <div class="card state-card k-memory"><div class="kicker">extraction</div><p class="small" style="margin:6px 0 0">Tribal knowledge — what <em>is</em> and what to <em>do</em> — from narratives, with no extraction code.</p></div>
          <div class="card state-card k-domain"><div class="kicker">findings + VECTOR</div><p class="small" style="margin:6px 0 0">Similar history by <span class="mono">VECTOR_DISTANCE()</span>, filtered, in one SQL statement.</p></div>
          <div class="card state-card k-sdk"><div class="kicker">scoping</div><p class="small" style="margin:6px 0 0">Multi-tenant safety in the database: private turns, shared knowledge.</p></div>
          <div class="card state-card k-memory"><div class="kicker">context card</div><p class="small" style="margin:6px 0 0">An inspector's own thread, compressed into a block that travels with every turn.</p></div>
          <div class="card state-card k-model"><div class="kicker">pooled search</div><p class="small" style="margin:6px 0 0">The next inspector inherits distilled lessons — never the raw transcript.</p></div>
          <div class="card state-card k-domain"><div class="kicker">CITY_ASSET</div><p class="small" style="margin:6px 0 0">The asset's structured record at the start of every turn.</p></div>
        </div>

        <h2>Where to next</h2>
        <ul class="tight">
          <li><a href="https://docs.oracle.com/en/database/oracle/agent-memory/" target="_blank" rel="noopener">Oracle AI Agent Memory documentation</a></li>
          <li><a href="https://github.com/oracle-devrel/oracle-ai-developer-hub" target="_blank" rel="noopener">Oracle AI Developer Hub</a></li>
          <li><a href="https://www.deeplearning.ai/short-courses/agent-memory-building-memory-aware-agents/" target="_blank" rel="noopener">Agent Memory: Building Memory-Aware Agents (DeepLearning.AI)</a></li>
        </ul>
        ${C.takeaway(`<p>Keep the system of record structured and deliberate, let memory grow from every turn, scope both in the database — and a stateless model becomes a copilot that remembers.</p>`)}`;
      if (!ctx.ready) return;
      api
        .get("overview")
        .then((o) => {
          const total = Object.values(o.memory_by_type).reduce((a, b) => a + b, 0);
          $("#mt-live", el).innerHTML =
            `<div class="card"><div class="kicker" style="--k:var(--c-memory)">in this workspace now</div>
          <div class="row" style="margin-top:8px">${Object.entries(o.memory_by_type)
            .map(([t, n]) => `${C.chip(t, `${t} · ${n}`)}`)
            .join("")}
          <span class="small faint">${total} records across ${o.threads} thread(s) · <a href="#" data-explore="MEMORY">browse them</a></span></div></div>`;
        })
        .catch(() => {});
    },
  });
})();
