/* Part 6 (durable memory in Oracle) and Part 7 (the memory aware agent). */

(() => {
  const { C, esc, api, $, trunc } = App;
  const F = D.F;
  const statusChip = (s) => C.chip(s === "valid" ? "ok" : s === "invalid" ? "err" : "", s || "–");
  const typeChip = (t) => C.chip(t, t);

  Object.assign(App.STEP_RENDER, {
    procedures: (d) => `${C.table(
      ["record_id", "type", "procedure"],
      d.stored.map((r) => [
        `<span class="mono small">${esc(r.id)}</span>`,
        typeChip(r.record_type),
        `<span class="small">${esc(r.content)}</span>`,
      ])
    )}
      <p class="small faint">Reused from an earlier attempt in this run: ${d.reused}. OAMP's tables: ${d.tables.map((t) => `<span class="mono">${esc(t)}</span>`).join(", ")}</p>`,
    threads: (d) => `<div class="status-grid">
        <div class="status-item"><div class="k">Alice</div><div class="v mono small">user ${esc(d.alice)}<br>thread ${esc(d.alice_thread)}</div></div>
        <div class="status-item"><div class="k">Bob</div><div class="v mono small">user ${esc(d.bob)}<br>thread ${esc(d.bob_thread)}</div></div></div>
      ${C.record({ memory_type: "fact", content: d.bob_note, user_id: d.bob, thread_id: d.bob_thread })}
      ${C.more("Alice's thread: the extraction configuration", C.json(d.extraction))}`,
    capture: (d) => {
      const byId = Object.fromEntries(d.extracted.map((r) => [r.id, r]));
      return `${C.table(
        ["capture step", "type", "status", "extracted content"],
        d.extracted.map((r) => [
          `<span class="mono small">${esc(r.capture_step)}</span>`,
          typeChip(r.record_type),
          statusChip(r.status),
          `<span class="small">${esc(r.content)}</span>`,
        ])
      )}
      <p class="small">${d.proposal_count} candidate(s) from the proposal, ${d.approval_count} from the approval — each check required records carrying <em>this</em> ingestion's <span class="mono">capture_id</span>.</p>
      ${
        d.inferred_links && d.inferred_links.length
          ? `<h3>Links OAMP inferred on its own</h3>${d.inferred_links.map((l) => `<p class="small">${C.chip("model", l.relation)} <span class="muted">${esc(trunc((byId[l.source] || {}).content || l.source, 70))}</span> → <span class="muted">${esc(trunc((byId[l.target] || {}).content || l.target, 70))}</span></p>`).join("")}
        <p class="small faint">Post-extraction linking ran an extra model call and may already mark the proposal superseded. The next step records the relationship explicitly, after review.</p>`
          : ""
      }`;
    },
    reviewed: (d) => `<div class="compare">
        <div><h3>Before the link</h3>${d.before.map((r) => C.record({ memory_type: "fact", content: r.content }, { extra: statusChip(r.status) })).join("")}</div>
        <div><h3>After <span class="mono">supersedes</span></h3>${d.after.map((r) => C.record({ memory_type: "fact", content: r.content }, { extra: statusChip(r.status) })).join("")}</div></div>
      ${C.checks(d.checks, { current_valid: "current fact valid", old_invalid: "old proposal invalid", search_hides_old: "search hides the old fact", linked_history: "one hop brings it back as history" })}
      ${C.more("The graph hit as OAMP formats it", C.code(d.current_hit_xml, "xml", { wrap: true }))}`,
    offload: (
      d
    ) => `<div class="grid2"><div><div class="msg-role">reference passed to the agent (${d.reference_chars} chars)</div>${C.json(d.reference)}</div>
        <div><div class="msg-role">bounded summary (${d.summary_chars} of ${d.source_chars} chars)</div><div class="answer plain small">${esc(d.summary)}</div></div></div>
      <p class="small faint">The summary is a lossy, unverified pointer — check it still says 80 was proposed, 120 approved, and nothing ordered.</p>`,
    memory_agent: (
      d
    ) => `${C.trace(d)}${C.checks(d, { recall_called: "recall_inventory was called", stage_restored: "a new client restored stage = awaiting-review", draft_restored: "…and the exact draft" })}
      ${C.more("What the host sent, and the scopes it chose", C.json(d.payload) + C.json(d.scopes))}`,
    fresh: (d) =>
      `${C.trace(d)}${C.checks(d, { recall_called: "the fresh agent called recall_inventory", current_fact_recalled: "Oracle returned the reviewed current fact" })}`,
  });

  /* ================================================================ Part 6 */

  App.page("part6", {
    accent: "var(--c-memory)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 6 · Retain and refine durable memory in Oracle</p>
        <h1>Memory that outlives the conversation</h1>
        <p class="lede">Store the procedures, give each planner a scope, capture the shift notes, let OAMP extract candidate memories in the background —
        then record the reviewed decision and supersede the old proposal without erasing it.</p>
        ${C.learn([
          ["See", "retain → extract → review → recall"],
          ["Meet", "users, threads, typed records, links"],
          ["TODOs", "3 · 4 · 5 · 6 · 7"],
        ])}
        ${C.fig(
          F.lifecycle(),
          `The automatic path (OAMP's extraction and linking) and the human review step are deliberately separate:
          extracted memories are a reusable <em>interpretation</em> of the messages, not verified business records.`
        )}

        <h2>One store, shared procedures</h2>
        <p class="small muted">OAMP names its tables after the store (the notebook's is <span class="mono">ZH_INVENTORY</span>, the appbook's
          <span class="mono">${esc((ctx.health || {}).store || "INVAPP")}</span>) and creates them on first use. The four SOPs go in as <b>shared guidelines</b>:
          <span class="mono">user_id=None</span>, metadata <span class="mono">source=approved-procedure</span>.</p>
        ${C.tryPanel("p6-proc", "Store the approved procedures", "Part 6.2–6.3 · no model calls", `<div id="p6-proc-step"></div>`)}

        <h2>Organise memory by user and thread</h2>
        ${C.fig(
          F.scopes(),
          `A <b>user ID</b> labels whose knowledge a record is; a <b>thread ID</b> groups one conversation or case. Bob's unrelated tote-bag case
          is the contrast — relevant versus irrelevant memory.`
        )}
        ${C.tryPanel("p6-threads", "Define planner labels and open both threads", "TODO 4 · no model calls", `<div id="p6-threads-step"></div>`)}

        <h2>Capture the case, extract in the background</h2>
        <p class="small muted">Each note goes in with <span class="mono">add_messages_async</span> and provenance metadata. OAMP extracts in the
          <b>background</b>; the check waits for it, fails on any SDK error or unsuccessful operation, and requires records from <em>this</em> ingestion.</p>
        ${C.tryPanel("p6-capture", "Capture both shift notes", "TODO 5 · extraction + linking + summaries, ≈ 40 s", `<div id="p6-capture-step"></div>`)}
        ${C.callout("gotcha", "Extraction is not verification", `<p>Read the extracted rows against the two notes. They are a model's interpretation — useful, reusable, and still to be checked.</p>`)}

        <h2>Evolve a decision without erasing history</h2>
        ${C.fig(
          F.supersede(),
          `Keeping only 80 is stale; deleting it loses how the decision changed; showing both as current misleads.
          A reviewed pair plus a <span class="mono">supersedes</span> link keeps all three problems away.`
        )}
        ${C.tryPanel("p6-reviewed", "Supersede the old proposal, then recall", "TODO 6–7 · no model calls", `<div id="p6-reviewed-step"></div>`)}
        ${C.takeaway(`<p>Retain is only the beginning: keep records you can find, interpret, trust appropriately and update — with history kept, not presented as current.</p>`)}`;
      App.stepPanel($("#p6-proc-step", el), "procedures", { label: "Store the procedures" });
      App.stepPanel($("#p6-threads-step", el), "threads", { label: "Open both threads" });
      App.stepPanel($("#p6-capture-step", el), "capture", { label: "Capture and extract" });
      App.stepPanel($("#p6-reviewed-step", el), "reviewed", { label: "Supersede and recall" });
    },
  });

  /* ================================================================ Part 7 */

  App.page("part7", {
    accent: "var(--c-memory)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 7 · Make the existing agent memory aware</p>
        <h1>The same loop, now with durable evidence</h1>
        <p class="lede">Offload the long worksheet, compact the conversation, give the same agent loop two memory tools — then ask from a brand-new session
        with the question alone.</p>
        ${C.learn([
          ["See", "offloading, compaction, host-chosen scopes"],
          ["Compare", "four agents on one question"],
          ["TODOs", "8 · 9 · 10 · 11"],
        ])}

        <h2>Offload the worksheet; compact the conversation</h2>
        <div id="p7-off">${F.offload()}</div>
        <p class="fig-cap">Store the full worksheet once and pass a short reference; keep a bounded summary for orientation — while the source messages stay retrievable.</p>
        ${C.tryPanel("p7-offload", "Offload and summarise", "TODO 8–9 · one summary call", `<div id="p7-offload-step"></div>`)}

        <h2>Attach memory tools to the same loop</h2>
        ${C.fig(
          F.memoryAgent(),
          `Same model, same factory — new capability: <span class="mono">recall_inventory</span> searches only the three scopes the host listed,
          and <span class="mono">inspect_stock_report</span> accepts only the one worksheet ID.`
        )}
        ${C.tryPanel("p7-agent", "Run the memory aware loop and persist its draft", "TODO 10–11", `<div id="p7-agent-step"></div>`)}

        <h2>Ask from a fresh session: question only</h2>
        <p class="small muted">A new Oracle client and a rebuilt agent receive exactly the question-only input from Part 5 — no notes, no summary, no reference.</p>
        ${C.tryPanel("p7-fresh", "Ask a fresh memory aware agent", "Part 7.3", `<div id="p7-fresh-step"></div>`)}

        <h2>Compare the actual answers as the agent evolves</h2>
        <div id="p7-journey">${F.journey([])}</div>
        <div id="p7-compare"></div>
        ${C.takeaway(`<p>The host controls capability: the same model answers correctly in a new conversation only because the host gave its loop a scoped path to reviewed evidence.</p>`)}`;
      App.stepPanel($("#p7-offload-step", el), "offload", {
        label: "Offload and summarise",
        onResult: (d) => ($("#p7-off", el).innerHTML = F.offload(d)),
      });
      App.stepPanel($("#p7-agent-step", el), "memory_agent", {
        label: "Run the memory aware loop",
      });
      App.stepPanel($("#p7-fresh-step", el), "fresh", {
        label: "Ask from a fresh session",
        onResult: () => loadComparison(el),
      });
      loadComparison(el);
    },
  });

  async function loadComparison(el) {
    if (!App.state.health || !App.state.health.ready) return;
    try {
      const st = await api.get("state");
      $("#p7-journey", el).innerHTML = F.journey(st.comparison);
      const last = st.comparison.find((r) => r.stage.startsWith("Memory aware"));
      const idSlip =
        last &&
        /Approval request:[^\n;]*RESTOCK-101/i.test(last.answer) &&
        !/Approval request:[^\n;]*PO-1048/i.test(last.answer);
      $("#p7-compare", el).innerHTML = st.comparison.length
        ? C.table(
            ["stage", "case evidence available", "actual answer"],
            st.comparison.map((r) => [
              esc(r.stage),
              esc(r.evidence),
              `<span class="small mono">${esc(r.answer)}</span>`,
            ])
          ) +
          (idSlip
            ? C.watch(`<p>Review the approval line: this answer names the case ID <span class="mono">RESTOCK-101</span> where the purchase request
            <span class="mono">PO-1048</span> belongs — although the recalled fact contains both. The notebook's saved run did the same. A correct quantity is not a correct citation.</p>`)
            : "")
        : C.empty("Run Parts 4, 5 and 7.3 (or the whole lab) to fill in the four stages.");
    } catch (e) {
      /* the page still reads without it */
    }
  }
})();
