/* Overview (notebook Parts 1–2) and Part 3 (services and the case). Diagram-first. */

(() => {
  const { C, esc, api, $ } = App;
  const F = D.F;

  /* ================================================================ overview */

  App.page("", {
    accent: "var(--c-domain)",
    render(el, ctx) {
      const h = ctx.health || {};
      el.innerHTML = `
        <p class="eyebrow">Everyday Goods · inventory replenishment · OAMP 26.8</p>
        <h1>Help the next planner pick up where the last shift stopped</h1>
        <p class="lede">An agent that drafts an inventory handover from the right evidence — the latest decision, its history and the reusable process —
        built step by step from a bare model to a memory aware agent on Oracle AI Agent Memory and Grok on OCI Generative AI.</p>
        <div id="ov-status"></div>

        <h2>The story</h2>
        ${C.fig(
          F.story(),
          `Approval, ordering and receiving stock are separate events. The next planner must learn that <b>120</b> mugs were approved under
          <b>PO-1048</b> — replacing the 80 proposed — and that <b>no supplier order</b> has been sent.`
        )}
        <div class="grid3">
          <div class="card state-card k-domain"><div class="kicker">friction</div><h3>Spread across notes</h3><p class="small muted">Request, approval and order status were written at different times.</p></div>
          <div class="card state-card k-model"><div class="kicker">friction</div><h3>80 and 120 both appear</h3><p class="small muted">The old proposal is easy to mistake for the current quantity.</p></div>
          <div class="card state-card k-memory"><div class="kicker">friction</div><h3>"Approved" read as "ordered"</h3><p class="small muted">Someone waits for a delivery that was never arranged.</p></div>
        </div>
        ${C.more(
          "All six frictions, and what the agent adds",
          C.table(
            ["Friction", "What the assistant adds"],
            [
              [
                "Request, approval and order status are in separate notes",
                "Recall the notes and a reviewed current fact in one conversation",
              ],
              [
                "Both 80 and 120 appear in the history",
                "Keep the proposal as history; mark the approval as its replacement",
              ],
              [
                "“Approved” is mistaken for “ordered”",
                "Preserve the explicit statement that no order was submitted",
              ],
              [
                "Long worksheets bury the useful update",
                "Store the worksheet; pass a short reference; fetch detail when needed",
              ],
              [
                "Each planner rewrites the same checklist",
                "Save a reviewed reusable procedure for future handovers",
              ],
              [
                "A persuasive draft names an owner without evidence",
                "Label unknowns; require human review before saving",
              ],
            ],
            "prose-table"
          )
        )}

        <h2>The system you will build</h2>
        ${C.fig(
          F.architecture("ZH_INVENTORY"),
          `Grok on OCI Generative AI does the language work through two clients; Oracle does storage, embeddings and vector search;
          OAMP manages memory; the host keeps the controls — which evidence tools may reach, and the human review gate.
          The appbook stores its copy under <span class="mono">${esc(h.store || "INVAPP")}_*</span>.`
        )}

        <h2>Four memory roles</h2>
        ${C.fig(
          F.memoryRoles(),
          `The context window is finite working space. Episodic, semantic and procedural memory are durable sources for rebuilding it —
          a record influences an answer only when the application retrieves it into that turn's context.`
        )}

        <h2>Context engineering and memory engineering</h2>
        ${C.fig(
          F.engineering(),
          `<b>Memory engineering</b> decides what becomes durable, how it evolves and how it comes back. <b>Context engineering</b> selects the
          right subset for this turn. More context is not automatically better: "120 approved; not ordered yet" beats a long unlabelled history.`
        )}

        <h2>The journey: one question, four agents</h2>
        <div id="ov-journey">${F.journey([])}</div>
        <p class="fig-cap">The same model and the same question each time; only the evidence the call can reach changes. The boxes show the notebook's
          saved run until you run the lab — then your own answers.</p>
        ${C.fig(F.roadmap(), `Click a Part to open it. Each Part adds one building block and runs the earlier steps it needs.`)}

        ${C.tryPanel(
          "ov-run",
          "Run the lab from the top",
          "≈ 2 minutes · about 23 Grok calls, billed to your OCI tenancy",
          `
          <p class="small">Runs every step of Parts 4–9 in the notebook's order in this lab run (cleanup stays on the Part 9 page). Each step's
          evidence then appears on its page.</p>
          <button class="btn primary" data-run-all>Run the whole lab</button><div id="ov-job"></div>`
        )}
        ${C.takeaway(`<p>Help people recover the decision before automating actions: durable memory supplies continuity; human review still decides whether a draft is fit to use.</p>`)}`;
      if (!ctx.ready) {
        $("#ov-status", el).innerHTML = ctx.notReady();
        return;
      }
      loadStatus($("#ov-status", el), ctx);
      $("[data-run-all]", el).onclick = (ev) => {
        ev.target.disabled = true;
        App.runJob(api.post("run-all"), $("#ov-job", el), {
          onDone: () => {
            ev.target.disabled = false;
            loadStatus($("#ov-status", el), ctx);
          },
          onError: () => {
            ev.target.disabled = false;
          },
        });
      };
    },
  });

  async function loadStatus(box, ctx) {
    try {
      const st = await api.get("state");
      const h = ctx.health;
      box.innerHTML = `<div class="status-grid">
        <div class="status-item"><div class="k"><span class="dot ok"></span>Oracle AI Database</div><div class="v mono small">${esc(h.db.user)}@${esc(h.db.dsn)}</div></div>
        <div class="status-item"><div class="k"><span class="dot ok"></span>OCI Generative AI</div><div class="v mono small">${esc(h.oci.model)} · ${esc(h.oci.region)}</div></div>
        <div class="status-item"><div class="k"><span class="dot ok"></span>Memory store</div><div class="v mono small">${esc(h.store)}_* · OAMP ${esc(h.versions.oracleagentmemory)}</div></div>
        <div class="status-item"><div class="k">This lab run</div><div class="v small"><span class="mono">${esc(st.run_id)}</span> · ${st.done.length} of ${st.steps.length} steps done</div></div>
      </div>`;
      if (st.comparison && st.comparison.length)
        $("#ov-journey", box.parentElement).innerHTML = F.journey(st.comparison);
    } catch (e) {
      box.innerHTML = C.error(e);
    }
  }

  /* ================================================================ Part 3 */

  Object.assign(App.STEP_RENDER, {
    connect: (d) => `${C.checks(d, { structured_ok: `structured JSON: ${d.structured}` })}
      <div class="checks">${C.chip("sdk", `embedding shape (${d.embedding_shape.join(", ")})`)} ${C.chip("model", `OAMP route ${d.oamp_route}`)} ${C.chip("", d.auth)}</div>
      <p class="small faint mono">${esc(
        Object.entries(d.versions || {})
          .map(([k, v]) => `${k} ${v}`)
          .join(" · ")
      )}</p>`,
  });

  App.page("part3", {
    accent: "var(--c-sdk)",
    render(el, ctx) {
      const h = ctx.health || {};
      const oci = h.oci || {};
      el.innerHTML = `
        <p class="eyebrow">Part 3 · Meet the services and load the case</p>
        <h1>The case, and the services that will reason about it</h1>
        <p class="lede">A small synthetic case file, an Oracle database with an embedding model already loaded, and a hosted model on OCI Generative AI.</p>
        <div id="p3-case"></div>

        <h2>Two clients, one hosted model</h2>
        ${C.fig(
          F.twoClients(oci.model || "xai.grok-4.3", oci.region || "us-chicago-1"),
          `The agent talks to Grok through LangChain's <span class="mono">ChatOpenAI</span>;
          OAMP talks to it through its own <span class="mono">Llm</span> client. A working agent call does not prove OAMP's route is authenticated — so both are checked.`
        )}
        ${C.term(
          "OCI Generative AI",
          `<p>Oracle Cloud's managed service for hosted language models, called over HTTP. <span class="mono">${esc(oci.model || "xai.grok-4.3")}</span> is a reasoning
          model: a low output budget can leave it with no answer, so both clients allow 4,096 tokens. An API key only works in the region it was created in
          (here <span class="mono">${esc(oci.region || "?")}</span>, ${esc(oci.auth || "")}).</p>`
        )}

        ${C.tryPanel(
          "p3-try",
          "Connect OAMP's model and the in-database embedder",
          "Part 6.1–6.2 · TODO 3",
          `
          <p class="small">Asks Grok, through OAMP's client, for a structured JSON object (what extraction needs) and embeds one sentence inside Oracle.</p>
          <div id="p3-step"></div>`
        )}
        ${C.takeaway(`<p>Name every service before relying on it: what each one does, how it is authenticated, and which one actually answered.</p>`)}`;
      loadCase($("#p3-case", el));
      App.stepPanel($("#p3-step", el), "connect", { label: "Run the connection checks" });
    },
  });

  async function loadCase(box) {
    try {
      const d = await api.get("case");
      box.innerHTML = `<div class="status-grid">
          <div class="status-item"><div class="k">case</div><div class="v mono">${esc(d.case_id)}</div></div>
          <div class="status-item"><div class="k">product</div><div class="v">${esc(d.product)} <span class="mono">${esc(d.sku)}</span></div></div>
          <div class="status-item"><div class="k">proposed → approved</div><div class="v"><b>${d.initial_quantity}</b> → <b>${d.approved_quantity}</b> under <span class="mono">${esc(d.approval_id)}</span></div></div>
          <div class="status-item"><div class="k">supplier order</div><div class="v">not submitted</div></div></div>
        <div class="grid3" style="margin-top:12px">
          <div class="card state-card k-domain"><div class="kicker">Alice · note</div><p class="small" style="margin:6px 0 0">${esc(d.alice_note)}</p></div>
          <div class="card state-card k-memory"><div class="kicker">Alice · update</div><p class="small" style="margin:6px 0 0">${esc(d.alice_update)}</p></div>
          <div class="card state-card k-model"><div class="kicker">Bob · unrelated case</div><p class="small" style="margin:6px 0 0">${esc(d.bob_note)}</p></div>
        </div>
        ${C.more(
          "The four approved procedures and the three evaluation questions",
          C.table(
            ["id", "procedure"],
            d.procedures.map((p) => [`<span class="mono">${esc(p.id)}</span>`, esc(p.text)])
          ) +
            C.table(
              ["evaluation question", "expected procedure"],
              d.evaluation.map((q) => [
                esc(q.query),
                `<span class="mono">${esc(q.expected)}</span>`,
              ])
            )
        )}`;
    } catch (e) {
      box.innerHTML = C.error(e);
    }
  }
})();
