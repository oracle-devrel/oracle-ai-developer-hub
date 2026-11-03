/* Part 8 (retrieval and working context), Part 9 (review, reuse, lifecycle) and the TODO map. */

(() => {
  const { C, esc, api, $, trunc } = App;
  const F = D.F;
  const short = (id) => String(id).replace(/-[0-9a-f]{10}$/, "");
  const ranked = (rows, expected) =>
    rows
      .map(
        (
          r
        ) => `<div class="record ${r.memory_type}" ${r.id === expected ? 'style="box-shadow:0 0 0 2px var(--d-ok)"' : ""}><div class="meta">
      <span>rank ${r.rank}</span>${C.chip(r.memory_type)}<span class="mono">${esc(short(r.id))}</span>${r.id === expected ? C.chip("ok", "expected") : ""}</div>
      <div class="body small">${esc(trunc(r.content, 220))}</div></div>`
      )
      .join("");

  Object.assign(App.STEP_RENDER, {
    retrieval: (d) =>
      d.evaluation
        .map(
          (q) => `<h3 style="margin-top:12px">${esc(q.question)}</h3>
      <div class="checks">${C.chip(q["hit@3"] ? "ok" : "err", `hit@3 = ${q["hit@3"]}`)} ${C.chip("", `${q.seconds}s`)} ${C.chip("", `expected: ${q.expected}`)}</div>
      <div class="records">${ranked(q.results, q.expected_id)}</div>`
        )
        .join(""),
    pruning: (d) => `<p class="small">Question: <em>${esc(d.query)}</em></p><div class="compare">
        <div><h3>${C.chip("", `unpruned · ${d.unpruned.length}`)}</h3><div class="records">${ranked(d.unpruned, d.expected_id)}</div></div>
        <div><h3>${C.chip("model", `pruned · ${d.pruned.length}`)}</h3><div class="records">${ranked(d.pruned, d.expected_id)}</div></div></div>
      ${C.checks({ ok: d["pruned_hit@3"] }, { ok: "the expected procedure survived pruning" })}`,
    observe: (d) =>
      C.table(
        ["#", "component", "event", "count"],
        d.events.map((e, i) => [
          i + 1,
          `<span class="mono">${esc(e.component)}</span>`,
          `<span class="mono">${esc(e.event)}</span>`,
          e.count,
        ])
      ),
    card: (
      d
    ) => `<div class="msg-role">handover draft · ${d.words} words</div><div class="answer">${esc(d.draft)}</div>
      ${C.more("The context card (unverified conversation context)", C.code(d.card, "xml", { wrap: true }) + C.json(d.card_settings))}
      ${C.more("The evidence object the model received", C.json(d.evidence))}`,
    scopes: (
      d
    ) => `${C.checks(d, { bob_in_bob_scope: "Bob's scope returns his record", alice_client_can_select_bob: "…and Alice's client can select it too" })}
      ${C.checks({ x: !d.bob_in_mug_scope }, { x: "the mug scope does not return Bob's record" })}
      <p class="small">Filters chose different records — but one database account read both. Alice and Bob are labels, not identities.</p>`,
    review: (
      d
    ) => `<div class="msg-role">the exact draft under review</div><div class="answer">${esc(d.draft)}</div>
      ${C.checks(d, { unapproved_write_blocked: "an unapproved write was blocked before database I/O" })}
      ${
        d.saved
          ? `<div class="approval">${C.chip("ok", "approved and saved")} receipt <span class="mono">${esc(d.saved.receipt_id)}</span></div>`
          : `
      <div class="approval"><div class="small"><b>You are the reviewer.</b> To save this exact draft, type the phrase below into the box. Anything else is refused.</div>
        <div class="code wrap" style="margin:8px 0"><pre><code>${esc(d.phrase)}</code></pre></div>
        <div class="row"><label style="flex:1 1 320px">approval phrase<input type="text" data-phrase placeholder="APPROVE …"></label>
          <button class="btn primary" data-approve>Approve and save</button><button class="btn" data-decline>Decline</button></div>
        <div data-approve-out></div></div>`
      }`,
    procedure: (
      d
    ) => `${C.record({ memory_type: "guideline", content: d.lesson.content })}${C.trace(d)}
      ${C.checks(d.checks, { procedure_recalled: "the lesson was recalled", no_case_ids: "no case IDs (PO-1048) leaked in" })}
      <p class="small faint">Extra steps in the checklist are the model's suggestions, not approved policy.</p>`,
    ttl: (d) =>
      `${C.checks({ a: d.search_hits === 0, b: d.row_count === 1 }, { a: `search: ${d.search_hits} hits — hidden`, b: `SQL: ${d.row_count} row — still stored` })}${C.code(d.sql, "sql")}`,
    cleanup: (d) => `${C.table(
      ["thread", "THREAD", "MESSAGE", "MEMORY", "RECORD_CHUNKS"],
      Object.keys(d.before).flatMap((k) => [
        [
          `<b>${esc(k)}</b> · before`,
          ...["THREAD", "MESSAGE", "MEMORY", "RECORD_CHUNKS"].map((c) => d.before[k][c]),
        ],
        [
          `${esc(k)} · after`,
          ...["THREAD", "MESSAGE", "MEMORY", "RECORD_CHUNKS"].map((c) => d.after[k][c]),
        ],
      ])
    )}
      ${C.checks(d, { all_zero: "both case threads now have zero rows" })}
      <p class="small">${d.shared_procedures_kept} shared procedure(s) kept, with their own TTL. Start a <b>New run</b> (sidebar) to go again.</p>`,
  });

  // The human decision, made in the page and checked by the host (never by the agent).
  document.addEventListener("click", async (ev) => {
    const box = ev.target.closest(".approval");
    if (!box) return;
    const out = $("[data-approve-out]", box);
    if (ev.target.closest("[data-decline]")) {
      out.innerHTML = `<p class="small">${C.chip("", "declined")} No approved handover was written.</p>`;
      return;
    }
    if (!ev.target.closest("[data-approve]")) return;
    try {
      const r = await api.post("approve", { phrase: $("[data-phrase]", box).value });
      out.innerHTML = `<p class="small">${C.chip("ok", "approved and saved")} receipt <span class="mono">${esc(r.receipt_id)}</span></p>`;
    } catch (e) {
      out.innerHTML = `<p class="small">${C.chip("err", "refused")} ${esc(e.message)}</p>`;
    }
  });

  /* ================================================================ Part 8 */

  App.page("part8", {
    accent: "var(--c-sdk)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 8 · Engineer retrieval and working context</p>
        <h1>Decide what the next model call sees</h1>
        <p class="lede">Inspect what recall returns and in what order, try LLM pruning, watch one search's operations, and assemble the next shift's working context.</p>
        ${C.learn([
          ["See", "ranked results, pruning, events"],
          ["Assemble", "a bounded context card + labelled evidence"],
          ["TODOs", "12 · 13 · 14"],
        ])}
        <div id="p8-ret">${F.retrieval()}</div>
        <p class="fig-cap">Three evaluation questions, each with an expected procedure: is it in the first three, and what else came back with it?</p>
        ${C.tryPanel("p8-retrieval", "Inspect vector-search results in returned order", "Part 8.1 · no model calls", `<div id="p8-retrieval-step"></div>`)}
        ${C.tryPanel("p8-pruning", "Compare result pruning", "TODO 12 · one Grok call per candidate", `<div id="p8-pruning-step"></div>`)}
        <h2>Observe operations without logging private memory</h2>
        <div id="p8-ev">${F.events()}</div>
        ${C.tryPanel("p8-observe", "Observe one memory search", "TODO 13", `<div id="p8-observe-step"></div>`)}
        <h2>Assemble the next shift's working context</h2>
        ${C.fig(
          F.contextCard(),
          `Authoritative evidence and conversational context are labelled separately. The card's <span class="mono">token_budget=1600</span> limits
          its relevant records only — recent messages, instructions and the answer need room too.`
        )}
        ${C.tryPanel("p8-card", "Assemble the card; generate the handover", "TODO 14 · summary + draft calls", `<div id="p8-card-step"></div>`)}
        ${C.takeaway(`<p>Context is an assembled view: inspect what recall returns, prune with care (smaller context has a cost), and label what is reviewed versus what is just conversation.</p>`)}`;
      let ev = null,
        pr = null;
      const redraw = () => ($("#p8-ret", el).innerHTML = F.retrieval(ev, pr));
      App.stepPanel($("#p8-retrieval-step", el), "retrieval", {
        label: "Run the three questions",
        onResult: (d) => {
          ev = d.evaluation[0];
          redraw();
        },
      });
      App.stepPanel($("#p8-pruning-step", el), "pruning", {
        label: "Prune the first question",
        onResult: (d) => {
          pr = d;
          redraw();
        },
      });
      App.stepPanel($("#p8-observe-step", el), "observe", {
        label: "Count the events",
        onResult: (d) => ($("#p8-ev", el).innerHTML = F.events(d.order)),
      });
      App.stepPanel($("#p8-card-step", el), "card", { label: "Build the card and draft" });
    },
  });

  /* ================================================================ Part 9 */

  App.page("part9", {
    accent: "var(--c-ok)",
    render(el, ctx) {
      el.innerHTML = `
        <p class="eyebrow">Part 9 · Review actions, reuse learning and manage the lifecycle</p>
        <h1>Review, reuse, expire — and delete only what you made</h1>
        <p class="lede">Separate relevance from permission, approve a write outside the model, turn the case into a reusable lesson, and see what expiry and cleanup really mean.</p>
        ${C.learn([
          ["See", "filters ≠ authorization; approval outside the model"],
          ["Reuse", "a reviewed lesson for the next product"],
          ["TODOs", "15 · 16 · 17"],
        ])}
        <h2>The boundary of retrieval scopes</h2>
        ${C.tryPanel("p9-scopes", "Compare the two product scopes", "TODO 15 · no model calls", `<div id="p9-scopes-step"></div>`)}
        ${C.callout("gotcha", "A different filter is not a different identity", `<p>Use separate database identities or schemas, not just labels, when people must not see each other's data.</p>`)}
        <h2>Review an action separately from generating it</h2>
        ${C.fig(F.reviewGate(), `A digest binds the approval phrase to this exact draft and run. The host — not the agent — compares it before writing.`)}
        ${C.tryPanel("p9-review", "Require review before a write", "TODO 16 · you approve or decline", `<div id="p9-review-step"></div>`)}
        <h2>Retain a reviewed lesson for the next product</h2>
        ${C.fig(F.reuse(), `A reusable procedure describes how to approach the next case — not this case's quantities or IDs.`)}
        ${C.tryPanel("p9-procedure", "Promote the lesson; reuse it", "TODO 17 · two Grok calls", `<div id="p9-procedure-step"></div>`)}
        <h2>Expiration is not erasure — and cleanup is narrow</h2>
        <div id="p9-ttl-fig">${F.ttl()}</div>
        ${C.tryPanel("p9-ttl", "Expire a record; count its row", "Part 9.4 · no model calls", `<div id="p9-ttl-step"></div>`)}
        ${C.tryPanel("p9-cleanup", "Delete only this run's two case threads", "Part 9.5 · ends this run", `<div id="p9-cleanup-step"></div>`)}
        ${C.takeaway(`<p>Keep claims narrow: filters are not permissions, approval stays outside the model, lessons are reviewed before reuse, and expired or deleted rows are scoped facts — not proof of erasure.</p>`)}`;
      let t = null,
        c = null;
      const redraw = () => ($("#p9-ttl-fig", el).innerHTML = F.ttl(t, c));
      App.stepPanel($("#p9-scopes-step", el), "scopes", { label: "Compare the scopes" });
      App.stepPanel($("#p9-review-step", el), "review", { label: "Put the draft under review" });
      App.stepPanel($("#p9-procedure-step", el), "procedure", {
        label: "Promote and reuse the lesson",
      });
      App.stepPanel($("#p9-ttl-step", el), "ttl", {
        label: "Run the expiry probe",
        onResult: (d) => {
          t = d;
          redraw();
        },
      });
      App.stepPanel($("#p9-cleanup-step", el), "cleanup", {
        label: "Delete this run's case threads",
        onResult: (d) => {
          c = d;
          redraw();
        },
      });
    },
  });

  /* ================================================================ TODO map */

  App.page("todos", {
    accent: "var(--c-ok)",
    render(el) {
      const T = [
        [1, "Ask the bare model", "Working memory and context", "part4"],
        [2, "Run the tool-using agent", "The agent loop without persistence", "part5"],
        [3, "Embed text inside Oracle", "Representations and model contracts", "part3"],
        [4, "Define planner labels", "User/thread scopes versus authorization", "part6"],
        [5, "Configure background extraction", "Turning episodes into typed memories", "part6"],
        [6, "Supersede the old proposal", "Refining knowledge while preserving history", "part6"],
        [7, "Recall current facts and linked history", "Graph-aware retrieval", "part6"],
        [8, "Configure bounded vector recall", "Retrieval limits and context budgets", "part7"],
        [9, "Offload the historical worksheet", "Episodic memory and source references", "part7"],
        [10, "Expose inventory recall", "Host-controlled evidence selection", "part7"],
        [11, "Run the memory aware loop", "Ingestion, recall and reasoning together", "part7"],
        [12, "Prune returned evidence", "Context selection versus stored knowledge", "part8"],
        [13, "Observe a memory search", "Local operation-level diagnostics", "part8"],
        [14, "Assemble a context card", "Bounded working-memory construction", "part8"],
        [15, "Compare the two product scopes", "Relevance filters are not permissions", "part9"],
        [16, "Require review before a write", "Action authority and exact-draft approval", "part9"],
        [17, "Reuse a reviewed lesson", "Procedural memory across cases", "part9"],
      ];
      el.innerHTML = `
        <p class="eyebrow">Wrap up · explain your 17 TODOs</p>
        <h1>What each step added to the system</h1>
        <p class="lede">The aim is understanding, not a coding test: for each TODO, say what it added and which problem from Part 1 it addresses.</p>
        ${C.fig(F.todoMap(), `Click a TODO to open the Part where it runs.`)}
        ${C.table(
          ["TODO", "what you did", "what it teaches", ""],
          T.map(([n, what, topic, part]) => [
            `<b>${n}</b>`,
            esc(what),
            `<span class="small muted">${esc(topic)}</span>`,
            `<a href="#/${part}" class="small">open</a>`,
          ])
        )}
        ${C.takeaway(`<p>Memory engineering prepares useful durable records; context engineering selects and presents the right subset for each turn —
          and the host keeps the authority to decide what the agent may read and what may be written.</p>`)}`;
    },
  });
})();
