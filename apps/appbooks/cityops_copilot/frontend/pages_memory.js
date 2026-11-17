/* Part 3 (memory + auto-extraction), Part 4 (findings + vector search), Part 5 (scoping). Diagram-first. */

(() => {
  const { C, esc, api, $, $$, trunc } = App;
  const F = D.F;
  const opt = (v, label, sel) =>
    `<option value="${esc(v)}" ${sel ? "selected" : ""}>${esc(label ?? v)}</option>`;
  const prefix = () => (App.state.health && App.state.health.prefix) || "CITYAPP_";

  async function assetOptions(selected, withAll) {
    const { assets } = await api.get("assets");
    return (
      (withAll ? opt("", "(all assets)", !selected) : "") +
      assets
        .map((a) => opt(a.asset_id, `${a.asset_id} · ${a.asset_class}`, a.asset_id === selected))
        .join("")
    );
  }

  /* shared job renderers for report_event-style jobs */
  const memRenderers = {
    write: (d) =>
      `<p class="small">add_messages() returned <span class="mono">${esc((d.message_ids || []).join(", "))}</span>. Extraction ran inside that call, so its records already exist.</p>`,
    diff: (
      d
    ) => `<h3>${esc(prefix())}MESSAGE · the verbatim record</h3>${C.records(d.messages, { max: 600 })}
      <h3>${esc(prefix())}MEMORY · what the extractor distilled</h3>${C.records(d.memories, { empty: "The extractor returned no records for this narrative." })}`,
  };
  for (let i = 1; i <= 8; i++) {
    memRenderers["n" + i] = (d) =>
      `<p class="small muted">${esc(d.narrative.narrative)}</p>${C.records(d.memories, { empty: "No records extracted." })}`;
  }

  const TYPES = [
    ["fact", "what <b>is</b> — durable realities", "Pier 2 bearings show recurring section loss"],
    ["preference", "stable choices and styles", "an inspector's usual measurement method"],
    ["guideline", "what to <b>do</b> — reusable rules", "remove loose corrosion before priming"],
    ["memory", "the fallback: ongoing state", "swap shifts with Jordan next Tuesday"],
  ];

  /* ================================================================ Part 3 */

  App.page("part3", {
    accent: "var(--c-memory)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 3 · City asset + auto-extraction</p>
        <h1>One call writes two kinds of memory</h1>
        <p class="lede"><span class="mono">thread.add_messages()</span> stores the inspector's narrative word for word <em>and</em> asks the SDK's LLM
        to distil reusable lessons from it, as typed records.</p>
        ${C.learn([
          ["See", "verbatim messages vs extracted records"],
          ["Read", "the real prompt the SDK sends its extractor"],
          ["Try", "reporting narratives and searching what they produce"],
        ])}

        <h2>One call, two memories</h2>
        ${C.fig(
          F.addMessages("CITY_"),
          `The message is kept exactly as written, in its thread — <b>episodic</b> memory. In the same call the extractor writes 2–8 short,
          standalone records that can be reused across threads and inspectors.`
        )}
        <div class="types">${TYPES.map(([t, what, ex]) => `<div class="type-card ${t}"><div class="k">${t}</div><div class="what">${what}</div><div class="ex">“${ex}”</div></div>`).join("")}</div>
        ${C.callout("gotcha", "Extraction is probabilistic", `<p>A small local model sometimes files a fact as a preference, or a rule as a fact. Re-run the narrative if a type looks wrong.</p>`)}
        ${C.more(
          "See report_event and the extraction prompt",
          C.code(`async def report_event(asset_id, inspector, narrative, thread_id) -> list:
    try:
        t = memory.get_thread(thread_id)
    except Exception:
        t = None
    if t is None:
        t = memory.create_thread(user_id=inspector, thread_id=thread_id, agent_id="CITY",
                                 enable_context_summary=True, context_summary_update_frequency=2)
    # The extractor only sees text, so name the asset and the inspector in it.
    content = f"[Asset: {asset_id}] [Inspector: {inspector}] {narrative}"
    return await t.add_messages_async([Message(role="user", content=content)])`) +
            `<p class="small muted">You don't write the extraction prompt — the SDK does. It opens like this (open the <i>SDK LLM · memory extraction</i> call in any job for the full text):</p>` +
            C.code(
              `You are a memory extraction module for an LLM agent.
Extract a small set of HIGH-VALUE, ATOMIC memory records … retrieved with FLAT semantic search.
1) Atomic   2) Standalone   3) Retrieval-optimized   …
- Produce between 2 and 8 memories.   - Do not invent details.`,
              "text",
              { wrap: true }
            )
        )}

        ${C.tryPanel(
          "p3-report",
          "Report narratives and watch extraction",
          "report_event()",
          `
          <div class="row"><button class="btn primary" data-demo>Run the notebook's sample</button>
            <span class="small faint">4 narratives (routine, warning, critical) as <span class="mono">inspector_demo</span> — one extractor call each, about a minute or two.</span></div>
          <div id="p3-demo-job"></div>
          <hr>
          <div class="form">
            <div class="row">
              <label>asset<select data-asset></select></label>
              <label>pick a narrative from the dataset<select data-pick><option value="">(choose an asset first)</option></select></label>
            </div>
            <label>narrative<textarea data-narr rows="3" placeholder="Pick one above, or write your own observation."></textarea></label>
            <div class="row">
              <label>inspector (the thread's user_id)<input type="text" data-insp value="inspector_demo"></label>
              <label>thread_id<input type="text" data-thread value="inspect_demo"></label>
              <button class="btn primary" data-report>Run report_event</button>
            </div>
          </div>
          <div id="p3-job"></div>`
        )}

        <h2>Searching memory: scope must match</h2>
        ${C.fig(
          F.scopeSearch(),
          `Records inherit the user_id of the thread that wrote them. <span class="mono">user_id=None</span> does <b>not</b> mean everyone —
          it means "records with no user". The SDK makes you state the scope on every search, so a forgotten argument can't widen one.`
        )}
        ${C.tryPanel(
          "p3-search",
          "Scoped memory search",
          "memory.search_async()",
          `
          <div class="form">
            <label>query<input type="text" data-q value="recurring asset concerns and inspector practices"></label>
            <div class="row">
              <label>user_id<select data-u>${opt("inspector_demo", 'user_id="inspector_demo"', true)}${opt("__none__", "user_id=None")}${opt("__custom__", "custom…")}</select></label>
              <label>custom user_id<input type="text" data-u-custom placeholder="e.g. Harbor Bridge"></label>
              <label>agent_id<input type="text" data-a value="CITY"></label>
            </div>
            <div class="row"><span class="small faint mono">record_types:</span>${["fact", "preference", "guideline", "memory", "message"].map((t) => `<label class="check"><input type="checkbox" data-rt value="${t}" ${t !== "message" ? "checked" : ""}> ${C.chip(t)}</label>`).join("")}
              <button class="btn primary" data-search>Search</button></div>
          </div><div id="p3-search-out"></div>`
        )}

        ${C.tryPanel(
          "p3-log",
          "The memory log",
          "view_memories() — an inspection view across all scopes",
          `
          <div class="row">
            <label>user_id<input type="text" data-f-user placeholder="any (e.g. inspector_demo, Harbor Bridge)"></label>
            <label>record type<select data-f-type>${opt("", "any")}${["fact", "preference", "guideline", "memory"].map((t) => opt(t)).join("")}</select></label>
            <label>thread_id<input type="text" data-f-thread placeholder="any"></label>
            <button class="btn" data-f-go>Show</button>
          </div><div id="p3-log-out"></div>`
        )}

        ${C.more("The asset registry behind it all", `<p class="small muted">26 assets, classified by a name rule into eight classes. Plain SQL, outside the SDK.</p><div id="p3-assets"></div>`)}
        ${C.takeaway(`<p>One <span class="mono">add_messages()</span> keeps the conversation and distils reusable records. You never write the extraction prompt; you choose the scope the records inherit.</p>`)}`;

      if (!ctx.ready) {
        ["#p3-assets", "#p3-demo-job", "#p3-log-out", "#p3-search-out"].forEach(
          (s) => ($(s, el).innerHTML = ctx.notReady())
        );
        return;
      }
      loadAssets($("#p3-assets", el));
      wireReport(el);
      wireLog(el);
      wireSearch(el);
    },
  });

  async function loadAssets(box) {
    try {
      const { assets } = await api.get("assets");
      const byClass = {};
      assets.forEach((a) => (byClass[a.asset_class] = (byClass[a.asset_class] || 0) + 1));
      const max = Math.max(...Object.values(byClass));
      box.innerHTML = `<div class="grid2">
        <div class="barlist">${Object.entries(byClass)
          .sort((a, b) => b[1] - a[1])
          .map(
            ([k, n]) =>
              `<div class="item"><span class="mono small">${esc(k)}</span>${C.bar(n / max, "var(--c-domain)")}<span class="mono small">${n}</span></div>`
          )
          .join("")}</div>
        <div>${C.table(
          ["asset", "class", "narratives", "findings"],
          assets.map((a) => [
            esc(a.asset_id),
            C.chip("domain", a.asset_class),
            `<span class="mono">${a.narratives}</span>`,
            `<span class="mono">${a.findings}</span>`,
          ])
        )}</div></div>`;
    } catch (e) {
      box.innerHTML = C.error(e);
    }
  }

  function wireReport(el) {
    const assetSel = $("[data-asset]", el),
      pick = $("[data-pick]", el),
      narr = $("[data-narr]", el);
    let narratives = [];
    assetOptions("Harbor Bridge").then((o) => {
      assetSel.innerHTML = o;
      loadNarr();
    });
    async function loadNarr() {
      const r = await api.get("narratives", { asset: assetSel.value, limit: 60 });
      narratives = r.narratives;
      pick.innerHTML =
        opt("", `(${r.total} narrative${r.total === 1 ? "" : "s"} for this asset)`) +
        narratives
          .map((n, i) => opt(String(i), `[${n.severity}] ${trunc(n.narrative, 90)}`))
          .join("");
    }
    assetSel.onchange = loadNarr;
    pick.onchange = () => {
      const n = narratives[+pick.value];
      if (n) narr.value = n.narrative;
    };
    $("[data-report]", el).onclick = () => {
      const body = {
        asset_id: assetSel.value,
        inspector: $("[data-insp]", el).value.trim(),
        narrative: narr.value.trim(),
        thread_id: $("[data-thread]", el).value.trim(),
      };
      App.runJob(api.post("report-event", body), $("#p3-job", el), {
        renderers: memRenderers,
        autoOpen: ["diff"],
      });
    };
    $("[data-demo]", el).onclick = () =>
      App.runJob(api.post("extraction-demo", { count: 4 }), $("#p3-demo-job", el), {
        renderers: memRenderers,
        autoOpen: ["n1", "n2", "n3", "n4"],
      });
  }

  function wireLog(el) {
    const go = async () => {
      const out = $("#p3-log-out", el);
      try {
        const r = await api.get("memories", {
          user_id: $("[data-f-user]", el).value.trim(),
          record_type: $("[data-f-type]", el).value,
          thread_id: $("[data-f-thread]", el).value.trim(),
          limit: 60,
        });
        out.innerHTML =
          `<p class="small faint" style="margin-top:10px">${r.memories.length} row(s), newest first.</p>` +
          C.records(r.memories, (m) => ({
            max: 400,
            extra: `<span>seq ${m.order_seq} · ${esc(m.created)}</span>`,
            empty: "No memories match. Run the sample above first.",
          }));
      } catch (e) {
        out.innerHTML = C.error(e);
      }
    };
    $("[data-f-go]", el).onclick = go;
    go();
  }

  function wireSearch(el) {
    $("[data-search]", el).onclick = async () => {
      const out = $("#p3-search-out", el);
      const u = $("[data-u]", el).value;
      const user_id =
        u === "__none__" ? null : u === "__custom__" ? $("[data-u-custom]", el).value.trim() : u;
      const body = {
        query: $("[data-q]", el).value,
        user_id,
        agent_id: $("[data-a]", el).value.trim() || null,
        record_types: $$("[data-rt]:checked", el).map((c) => c.value),
        max_results: 20,
      };
      out.innerHTML = `<div class="small faint" style="margin-top:10px">Searching…</div>`;
      try {
        const r = await api.post("search", body);
        out.innerHTML = `${C.code(
          `await memory.search_async(query=${JSON.stringify(r.query)}, ${Object.entries(r.call)
            .map(([k, v]) => `${k}=${v === null ? "None" : JSON.stringify(v)}`)
            .join(", ")})`,
          "python",
          { wrap: true }
        )}
          <p class="small faint">${r.results.length} result(s) in ${r.ms} ms, ordered by relevance.</p>
          ${C.records(r.results, { max: 400, empty: user_id === null ? "Nothing — no record here belongs to “no user”. Set the user_id the records were written with." : "No records for this scope yet." })}`;
      } catch (e) {
        out.innerHTML = C.error(e);
      }
    };
  }

  /* ================================================================ Part 4 */

  App.page("part4", {
    accent: "var(--c-domain)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 4 · Inspection findings + similar-finding search</p>
        <h1>Structured findings, searched by meaning</h1>
        <p class="lede">A finding has a category, a severity, a grade and a recommendation — it is the formal record, not a memory. It lives in its own
        table with a vector column, so the copilot can find <em>similar</em> findings, filtered, in one SQL statement.</p>
        ${C.learn([
          ["See", "memory records vs domain objects"],
          ["Meet", "VECTOR(384), HNSW and VECTOR_DISTANCE()"],
          ["Try", "filtered similarity search, and logging a finding"],
        ])}

        <div class="grid2">
          <div class="card state-card k-memory"><div class="kicker">memory record</div><h3>Distilled · typed · scoped</h3>
            <p class="muted small">A sentence the extractor wrote. Good for lessons. Can't carry a finding's own fields.</p></div>
          <div class="card state-card k-domain"><div class="kicker">domain object</div><h3>Structured · deliberate · authoritative</h3>
            <p class="muted small">A row an inspector chose to record — never written by the model.</p></div>
        </div>

        <h2>Similarity and filters in one SQL statement</h2>
        ${C.fig(
          F.hybrid(),
          `The narrative is embedded, then one statement filters by asset and category, ranks by <span class="mono">VECTOR_DISTANCE</span>
          and keeps the top k. The <span class="mono">(:bind IS NULL OR col = :bind)</span> trick switches a filter off without building SQL strings.`
        )}

        <h2>How the HNSW index finds neighbours</h2>
        ${C.fig(
          F.hnsw(),
          `Each vector links to its nearest neighbours, in layers. A search makes long hops on the sparse top layer, then short
          local hops below — comparing the query with a small fraction of the rows. (<span class="mono">M 16, EFCONSTRUCTION 200, TARGET ACCURACY 95</span>.)`
        )}
        ${C.more(
          "See the table and the query",
          C.code(
            `CREATE TABLE CITY_INSPECTION_FINDING (
    finding_id VARCHAR2(64) PRIMARY KEY,  asset_id VARCHAR2(128) NOT NULL,
    inspector VARCHAR2(128),  overall_grade VARCHAR2(2),  category VARCHAR2(32),  severity VARCHAR2(16),
    description CLOB NOT NULL,  recommendation CLOB,  days_ago NUMBER,
    embedding VECTOR(384) NOT NULL,
    CONSTRAINT fk_finding_asset FOREIGN KEY (asset_id) REFERENCES CITY_ASSET(asset_id)
);
CREATE VECTOR INDEX city_finding_embedding_idx ON CITY_INSPECTION_FINDING (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95
  PARAMETERS (TYPE HNSW, M 16, EFCONSTRUCTION 200);

SELECT finding_id, asset_id, inspector, overall_grade, category, severity,
       description, recommendation, days_ago,
       VECTOR_DISTANCE(embedding, :q, COSINE) AS score
  FROM CITY_INSPECTION_FINDING
 WHERE (:asset_id IS NULL OR asset_id = :asset_id)
   AND (:category IS NULL OR category = :category)
 ORDER BY score
 FETCH FIRST :k ROWS ONLY`,
            "sql"
          )
        )}

        <div id="p4-summary"></div>
        ${C.tryPanel(
          "p4-search",
          "Find similar findings",
          "find_similar_findings()",
          `
          <div class="form">
            <label>describe what you see<input type="text" data-d value="bearing corrosion at piers"></label>
            <div class="row">
              <label>asset filter<select data-asset><option value="">(all assets)</option></select></label>
              <label>category filter<select data-cat><option value="">(all categories)</option></select></label>
              <label style="flex:0 0 90px">k<input type="number" data-k value="5" min="1" max="20"></label>
              <button class="btn primary" data-go>Search</button>
            </div>
            <div class="row"><button class="btn small" data-checkpoint>Run the notebook's TODO 5 checkpoint</button>
              <span class="small faint">broad, Harbor Bridge only, corrosion only — and check each filter held.</span></div>
          </div><div id="p4-out"></div>`
        )}

        ${C.tryPanel(
          "p4-log",
          "Log a finding",
          "log_finding() — the deliberate write: embed + INSERT, no model, ~0.1 s",
          `
          <div class="form">
            <div class="row">
              <label>asset<select data-l-asset></select></label>
              <label>inspector<input type="text" data-l-insp value="checkpoint_test"></label>
              <label>category<select data-l-cat></select></label>
              <label>severity<select data-l-sev>${["low", "medium", "high", "critical"].map((s) => opt(s, s, s === "medium")).join("")}</select></label>
              <label style="flex:0 0 90px">grade<select data-l-grade>${["A", "B", "C", "D", "F"].map((g) => opt(g, g, g === "C")).join("")}</select></label>
            </div>
            <label>description<textarea data-l-desc rows="2">Surface corrosion on pier 2 bearing assemblies; ~25% section loss observed.</textarea></label>
            <label>recommendation<textarea data-l-rec rows="2">Remove corrosion, apply primer + finish coat within 60 days.</textarea></label>
            <div class="row"><button class="btn primary" data-l-go>Log finding</button><span class="small faint">The notebook's TODO 4 checkpoint logs exactly this.</span></div>
          </div><div id="p4-log-out"></div>`
        )}

        ${C.takeaway(`<p>Keep the system of record structured and deliberate, and give it a vector column: Oracle answers "what looks like this, on this asset?" in one statement.</p>`)}`;
      if (!ctx.ready) {
        ["#p4-summary", "#p4-out", "#p4-log-out"].forEach(
          (s) => ($(s, el).innerHTML = ctx.notReady())
        );
        return;
      }
      wirePart4(el);
    },
  });

  async function wirePart4(el) {
    const summaryBox = $("#p4-summary", el);
    async function loadSummary() {
      try {
        const s = await api.get("findings");
        const max = Math.max(1, ...s.by_category.map((c) => c.n));
        summaryBox.innerHTML = `<div class="card"><div class="grid2"><div>
          <div class="kicker" style="--k:var(--c-domain)">loaded now</div><h3 style="margin-top:4px">${s.total} of ${s.dataset_total} dataset findings</h3>
          <p class="small muted">HNSW index: ${s.hnsw ? C.chip("ok", "present") : C.chip("err", "not created — searches scan the table")} · logged by hand: ${s.logged.length}</p>
          ${s.total < s.dataset_total ? `<button class="btn small" data-loadall>Load all ${s.dataset_total}</button> <span class="small faint">the notebook loads the first 15</span>` : ""}
          <div id="p4-load-job"></div></div>
          <div><div class="barlist">${s.by_category.map((c) => `<div class="item"><span class="mono small">${esc(c.category)}</span>${C.bar(c.n / max, "var(--c-domain)")}<span class="mono small">${c.n}</span></div>`).join("")}</div></div></div></div>`;
        const la = $("[data-loadall]", summaryBox);
        if (la)
          la.onclick = () => {
            la.disabled = true;
            App.runJob(api.post("findings/load-all"), $("#p4-load-job", summaryBox), {
              onDone: () => setTimeout(loadSummary, 200),
            });
          };
        $("[data-cat]", el).innerHTML =
          opt("", "(all categories)") + s.categories.map((c) => opt(c)).join("");
        $("[data-l-cat]", el).innerHTML = s.categories
          .map((c) => opt(c, c, c === "corrosion"))
          .join("");
        return s;
      } catch (e) {
        summaryBox.innerHTML = C.error(e);
      }
    }
    await loadSummary();
    $("[data-asset]", el).innerHTML = await assetOptions("", true);
    $("[data-l-asset]", el).innerHTML = await assetOptions("Harbor Bridge", false);

    const out = $("#p4-out", el);
    $("[data-go]", el).onclick = async () => {
      const body = {
        description: $("[data-d]", el).value,
        asset_id: $("[data-asset]", el).value || null,
        category: $("[data-cat]", el).value || null,
        k: +$("[data-k]", el).value || 5,
      };
      out.innerHTML = `<div class="small faint" style="margin-top:10px">Searching…</div>`;
      try {
        const r = await api.post("findings/search", body);
        out.innerHTML = `<p class="small faint" style="margin-top:12px">${r.rows.length} row(s) in ${r.ms} ms. Lower distance = more similar.</p>
          ${C.findings(r.rows)}
          ${C.more("The SQL and its bind values", C.code(r.sql, "sql") + C.json(r.binds))}`;
      } catch (e) {
        out.innerHTML = C.error(e);
      }
    };
    $("[data-checkpoint]", el).onclick = async () => {
      out.innerHTML = `<div class="small faint" style="margin-top:10px">Running three searches…</div>`;
      try {
        const q = "bearing corrosion at piers";
        const [broad, bridge, corr] = await Promise.all([
          api.post("findings/search", { description: q, k: 5 }),
          api.post("findings/search", { description: q, asset_id: "Harbor Bridge", k: 5 }),
          api.post("findings/search", { description: q, category: "corrosion", k: 5 }),
        ]);
        const ok = (b) => (b ? C.chip("ok", "pass") : C.chip("err", "fail"));
        out.innerHTML = `${C.table(
          ["search", "hits", "check", ""],
          [
            ["broad (no filter)", broad.rows.length, "at least 3 hits", ok(broad.rows.length >= 3)],
            [
              "asset_id = Harbor Bridge",
              bridge.rows.length,
              "every hit is Harbor Bridge",
              ok(bridge.rows.length && bridge.rows.every((r) => r.asset_id === "Harbor Bridge")),
            ],
            [
              "category = corrosion",
              corr.rows.length,
              "every hit is corrosion",
              ok(corr.rows.length && corr.rows.every((r) => r.category === "corrosion")),
            ],
          ]
        )}<h3>Harbor Bridge hits</h3>${C.findings(bridge.rows)}`;
      } catch (e) {
        out.innerHTML = C.error(e);
      }
    };
    $("[data-l-go]", el).onclick = async () => {
      const lo = $("#p4-log-out", el);
      try {
        const r = await api.post("findings/log", {
          asset_id: $("[data-l-asset]", el).value,
          inspector: $("[data-l-insp]", el).value.trim(),
          category: $("[data-l-cat]", el).value,
          severity: $("[data-l-sev]", el).value,
          overall_grade: $("[data-l-grade]", el).value,
          description: $("[data-l-desc]", el).value.trim(),
          recommendation: $("[data-l-rec]", el).value.trim(),
          days_ago: 0,
        });
        lo.innerHTML = `<p class="small" style="margin-top:10px">${C.chip("ok", "logged")} finding <span class="mono">${esc(r.finding_id)}</span> — searchable straight away.
          <a href="#" data-explore="INSPECTION_FINDING|inspector|${esc($("[data-l-insp]", el).value.trim())}">See the row</a>.</p>`;
        loadSummary();
      } catch (e) {
        lo.innerHTML = C.error(e);
      }
    };
  }

  /* ================================================================ Part 5 */

  const PRESETS = [
    {
      id: "vance",
      label: "Vance's personal scope",
      q: "shift swap notes",
      body: { user_id: "Jordan_Vance", record_types: ["memory"] },
    },
    {
      id: "mercer",
      label: "Mercer's personal scope",
      q: "shift swap notes",
      body: { user_id: "Evelyn_H_Mercer", record_types: ["memory"] },
    },
    {
      id: "city",
      label: "City-wide: agent CITY, no user",
      q: "Harbor Bridge Pier 2 bearings",
      body: { user_id: null, agent_id: "CITY", record_types: ["memory"] },
    },
    {
      id: "asset",
      label: "Harbor Bridge, pooled across inspectors",
      q: "Pier 2 bearing corrosion",
      body: {
        user_id: "Harbor Bridge",
        agent_id: "CITY",
        exact_thread_match: false,
        record_types: ["fact", "guideline", "memory"],
      },
    },
    {
      id: "thread",
      label: "One thread: Harbor Bridge::Evelyn_H_Mercer",
      q: "Pier 2 bearing corrosion",
      body: {
        user_id: "Harbor Bridge",
        agent_id: "CITY",
        thread_id: "Harbor Bridge::Evelyn_H_Mercer",
        record_types: ["fact", "guideline", "memory", "message"],
      },
    },
  ];

  function explainScope(b) {
    const user =
      b.user_id === null
        ? `<b>user_id</b> is empty — only records that belong to <em>no</em> user`
        : `<b>user_id</b> = <span class="mono">${esc(b.user_id)}</span>`;
    const agent = b.agent_id
      ? `<b>agent_id</b> = <span class="mono">${esc(b.agent_id)}</span>`
      : `<b>agent_id</b>: not given, so not constrained`;
    const thread = b.thread_id
      ? `<b>thread_id</b> = <span class="mono">${esc(b.thread_id)}</span>`
      : b.exact_thread_match === false
        ? `<b>thread_id</b>: any thread (<span class="mono">exact_thread_match=False</span>)`
        : `<b>thread_id</b>: not given, so not constrained`;
    return `<ul class="tight small"><li>${user}</li><li>${agent}</li><li>${thread}</li>
      <li><b>record types</b>: ${(b.record_types || []).map((t) => C.chip(t)).join(" ") || "any"}</li></ul>`;
  }

  App.page("part5", {
    accent: "var(--c-sdk)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 5 · Scoping — inspector vs city</p>
        <h1>Shared memory needs walls</h1>
        <p class="lede">Three scope dimensions on every record and every search, enforced as SQL predicates in the database — not as instructions in a prompt.</p>
        ${C.learn([
          ["See", "who can read which memory"],
          ["Meet", "the copilot's rule: private turns, shared knowledge"],
          ["Try", "the leak test and a scope explorer"],
        ])}

        <h2>Who can see what</h2>
        ${C.fig(
          F.scopeMap(),
          `The copilot files every thread under the <b>asset</b> (<span class="mono">user_id = Harbor Bridge</span>). Raw messages stay in each
          inspector's thread; the distilled records pool under the asset, so the next inspector inherits the lessons without the transcript.`
        )}
        <div class="grid3">
          <div class="card"><div class="kicker" style="--k:var(--c-memory)">user_id</div><p class="small" style="margin:6px 0 0">whose memory: an inspector for personal notes, or <b>the asset</b> for shared copilot memory</p></div>
          <div class="card"><div class="kicker" style="--k:var(--c-sdk)">agent_id</div><p class="small" style="margin:6px 0 0"><span class="mono">CITY</span>, the application — several agents can share one database</p></div>
          <div class="card"><div class="kicker" style="--k:var(--c-model)">thread_id</div><p class="small" style="margin:6px 0 0"><span class="mono">&lt;asset&gt;::&lt;inspector&gt;</span> — which conversation a record came from</p></div>
        </div>

        ${C.tryPanel(
          "p5-demo",
          "The notebook's leak test",
          "add_memory() + search_async() · no model calls",
          `
          <p class="small">Mercer writes a personal note and a city-wide guideline; then Vance searches twice, and Mercer once.</p>
          <button class="btn primary" data-demo>Run the scoping demo</button><div id="p5-job"></div>`
        )}

        ${C.tryPanel(
          "p5-explore",
          "Scope explorer",
          "same query, different walls",
          `
          <div class="form"><div class="row">
            <label>scope<select data-preset>${PRESETS.map((p) => opt(p.id, p.label)).join("")}</select></label>
            <label>query<input type="text" data-q></label>
            <button class="btn primary" data-go>Search</button></div>
            <div id="p5-explain"></div></div><div id="p5-out"></div>`
        )}
        <p class="small faint">The asset and thread presets find records once the copilot has run for Harbor Bridge (Part 6 or the handoff story).</p>
        ${C.takeaway(`<p>Scope is part of the data model, not the prompt: choose the principal deliberately, keep raw turns private, and let the database enforce the walls.</p>`)}`;

      const sel = $("[data-preset]", el),
        q = $("[data-q]", el);
      const show = () => {
        const p = PRESETS.find((x) => x.id === sel.value);
        q.value = p.q;
        $("#p5-explain", el).innerHTML =
          `<div class="small faint mono">this search matches records where:</div>${explainScope(p.body)}`;
      };
      sel.onchange = show;
      show();
      if (!ctx.ready) {
        $("#p5-job", el).innerHTML = ctx.notReady();
        return;
      }
      const searchView = (d) =>
        `${C.code(
          `search_async(${JSON.stringify(d.query)}, ${Object.entries(d.call)
            .map(([k, v]) => `${k}=${v === null ? "None" : JSON.stringify(v)}`)
            .join(", ")})`,
          "python",
          { wrap: true }
        )}${C.records(d.results, { empty: "No hits." })}`;
      $("[data-demo]", el).onclick = () =>
        App.runJob(api.post("scoping-demo"), $("#p5-job", el), {
          autoOpen: ["personal", "city"],
          renderers: {
            write: (d) =>
              `${C.record({ memory_type: "memory", content: d.personal.content, user_id: d.personal.user_id })}${C.record({ memory_type: "memory", content: d.city.content, user_id: null, agent_id: d.city.agent_id })}`,
            personal: searchView,
            city: searchView,
            mercer: searchView,
          },
          onDone: (job) => {
            const c = job.result.checks;
            $("#p5-job", el).insertAdjacentHTML(
              "beforeend",
              `<div class="row" style="margin-top:10px">${c.no_leak ? C.chip("ok", "no leak: Vance cannot see Mercer's note") : C.chip("err", "LEAK")}
            ${c.city_visible ? C.chip("ok", "Vance can see the city-wide guideline") : C.chip("err", "city guideline not found")}</div>`
            );
          },
        });
      $("[data-go]", el).onclick = async () => {
        const p = PRESETS.find((x) => x.id === sel.value);
        const out = $("#p5-out", el);
        try {
          out.innerHTML = searchView(
            await api.post("search", { ...p.body, query: q.value, max_results: 10 })
          );
        } catch (e) {
          out.innerHTML = C.error(e);
        }
      };
    },
  });
})();
