/* Inventory handover appbook — shell, shared components, jobs, Data Explorer.
   Pages register themselves with App.page(route, {title, render}). */

const App = (() => {
  const pages = {};
  const state = { health: null, route: null, jobs: [], drawerTable: null };

  const NAV = [
    {
      group: "Understand",
      items: [
        ["", "The handover problem", "1–2"],
        ["part3", "Services and the case", "3"],
      ],
    },
    {
      group: "Without memory",
      items: [
        ["part4", "A bare LLM", "4"],
        ["part5", "An agent loop", "5"],
      ],
    },
    {
      group: "With memory",
      items: [
        ["part6", "Durable memory in Oracle", "6"],
        ["part7", "The memory aware agent", "7"],
        ["part8", "Retrieval and working context", "8"],
        ["part9", "Review, reuse, lifecycle", "9"],
      ],
    },
    { group: "Wrap up", items: [["todos", "Your 17 TODOs", "✓"]] },
  ];
  const ORDER = NAV.flatMap((g) => g.items.map((i) => i[0]));
  const TITLES = Object.fromEntries(NAV.flatMap((g) => g.items.map((i) => [i[0], i[1]])));

  /* ------------------------------------------------------------ helpers */

  const esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
    );
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const fmtMs = (ms) => (ms == null ? "" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
  const trunc = (s, n) => {
    s = String(s ?? "");
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  };

  async function request(method, path, body) {
    const res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }
    if (!res.ok) {
      let detail = data && data.detail;
      if (Array.isArray(detail))
        detail = detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join("; ");
      throw new Error(detail || `${res.status} ${res.statusText}`);
    }
    return data;
  }
  const api = {
    get: (p, params) => {
      const q = params
        ? "?" +
          new URLSearchParams(
            Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
          ).toString()
        : "";
      return request("GET", "api/" + p + q);
    },
    post: (p, body) => request("POST", "api/" + p, body || {}),
  };

  /* ------------------------------------------------------- components */

  const C = {};
  C.callout = (kind, title, html) => {
    const icons = {
      term: "💡",
      memtype: "🧠",
      watch: "👀",
      notebook: "📓",
      gotcha: "⚠️",
      takeaway: "📌",
    };
    return `<div class="callout ${kind}"><div class="ic">${icons[kind] || "•"}</div><div><div class="ttl">${title}</div>${html}</div></div>`;
  };
  C.term = (title, html) => C.callout("term", `Key term — ${title}`, html);
  C.watch = (html) => C.callout("watch", "What to watch", html);
  C.notebook = (html) => C.callout("notebook", "In the notebook", html);
  C.takeaway = (html) => C.callout("takeaway", "Key takeaway", html);
  C.learn = (items) =>
    `<div class="learn">${items.map(([b, t]) => `<div><b>${b}</b>${t}</div>`).join("")}</div>`;
  C.chip = (type, label) => `<span class="chip ${esc(type)}">${esc(label ?? type)}</span>`;
  C.tryPanel = (id, title, sub, body) => `
    <section class="try" id="${id}">
      <div class="try-head"><span class="tag">Try it</span><span class="ttl">${title}</span>${sub ? `<span class="sub">${sub}</span>` : ""}</div>
      <div class="try-body">${body}</div>
    </section>`;
  C.figure = (src, caption) => `
    <figure><div class="figure-frame" data-zoom="${esc(src)}"><img src="${esc(src)}" alt="${esc(caption)}" loading="lazy" /></div>
    <figcaption>${caption}</figcaption></figure>`;
  C.table = (headers, rows, cls = "") => `
    <div class="tbl-wrap"><table class="${cls}"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  C.empty = (text) => `<div class="empty">${text}</div>`;
  C.fig = (svgHtml, caption) => `${svgHtml}<p class="fig-cap">${caption}</p>`;
  C.more = (summary, html) =>
    `<details class="more"><summary>${summary}</summary><div>${html}</div></details>`;
  C.error = (err) => `<div class="error-box">${esc(err && err.message ? err.message : err)}</div>`;
  C.bar = (frac, color) =>
    `<div class="bar"><span style="width:${Math.max(2, Math.min(100, frac * 100)).toFixed(1)}%;${color ? `--c:${color}` : ""}"></span></div>`;

  const PY_KW = new Set(
    "def async await return if else elif for in not and or is None True False try except with as import from class lambda raise while pass yield".split(
      " "
    )
  );
  const SQL_KW = new Set(
    "SELECT FROM WHERE AND OR NOT NULL IS ORDER BY FETCH FIRST ROWS ONLY CREATE TABLE INDEX VECTOR ON PRIMARY KEY FOREIGN REFERENCES CONSTRAINT INSERT INTO VALUES DEFAULT TIMESTAMP DROP CASCADE CONSTRAINTS ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY PARAMETERS TYPE AS USING DUAL COUNT GROUP JOIN LEFT IN SET UPDATE NEXT OFFSET".split(
      " "
    )
  );
  function highlight(src, lang) {
    if (lang === "xml") {
      return esc(src).replace(/&lt;\/?[a-z_]+&gt;/g, (m) => `<span class="xml-tag">${m}</span>`);
    }
    if (lang !== "sql" && lang !== "python") return esc(src);
    const re =
      lang === "sql"
        ? /(--[^\n]*)|('(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)/g
        : /(#[^\n]*)|("""[\s\S]*?"""|f?"(?:[^"\\\n]|\\.)*"|f?'(?:[^'\\\n]|\\.)*')|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)/g;
    const kw = lang === "sql" ? SQL_KW : PY_KW;
    let out = "",
      last = 0,
      m;
    while ((m = re.exec(src))) {
      out += esc(src.slice(last, m.index));
      const [tok, com, str, num, word] = m;
      if (com) out += `<span class="tok-c">${esc(tok)}</span>`;
      else if (str) out += `<span class="tok-s">${esc(tok)}</span>`;
      else if (num) out += `<span class="tok-n">${esc(tok)}</span>`;
      else if (word && kw.has(lang === "sql" ? word.toUpperCase() : word))
        out += `<span class="tok-k">${esc(tok)}</span>`;
      else if (word && src[m.index + tok.length] === "(")
        out += `<span class="tok-f">${esc(tok)}</span>`;
      else out += esc(tok);
      last = m.index + tok.length;
    }
    return out + esc(src.slice(last));
  }
  C.code = (src, lang = "python", opts = {}) =>
    `<div class="code ${opts.wrap ? "wrap" : ""}"><span class="lang">${esc(lang)}</span><pre><code>${highlight(String(src).replace(/^\n+|\s+$/g, ""), lang)}</code></pre></div>`;
  C.json = (data) =>
    `<div class="code wrap"><span class="lang">json</span><pre><code>${esc(JSON.stringify(data, null, 2))}</code></pre></div>`;

  C.record = (r, opts = {}) => {
    const type = r.record_type || r.memory_type || (r.role ? "message" : "memory");
    const bits = [C.chip(type)];
    if (r.role) bits.push(`<span>${esc(r.role)}</span>`);
    if (r.user_id !== undefined) bits.push(`<span>user_id=${esc(r.user_id ?? "None")}</span>`);
    if (r.thread_id) bits.push(`<span>thread=${esc(r.thread_id)}</span>`);
    if (r.agent_id && opts.agent !== false) bits.push(`<span>agent=${esc(r.agent_id)}</span>`);
    if (r.importance != null) bits.push(`<span>importance ${esc(r.importance)}</span>`);
    if (opts.extra) bits.push(opts.extra);
    return `<div class="record ${esc(type)} ${opts.highlight ? "highlight" : ""}"><div class="meta">${bits.join("")}</div><div class="body">${esc(opts.max ? trunc(r.content, opts.max) : r.content)}</div></div>`;
  };
  C.records = (rows, opts = {}) =>
    rows && rows.length
      ? `<div class="records">${rows.map((r) => C.record(r, typeof opts === "function" ? opts(r) : opts)).join("")}</div>`
      : C.empty(opts.empty || "No records.");

  C.findings = (rows, opts = {}) => {
    if (!rows || !rows.length) return C.empty(opts.empty || "No findings matched.");
    const max = Math.max(...rows.map((r) => r.score ?? 0), 0.0001);
    return C.table(
      [
        "distance",
        "asset",
        "category / severity",
        "inspector · grade",
        "description",
        "recommendation",
      ],
      rows.map((r) => [
        r.score != null
          ? `<div class="mono small">${r.score.toFixed(3)}</div>${C.bar(r.score / Math.max(max, 0.6), "var(--c-domain)")}`
          : "",
        esc(r.asset_id),
        `${C.chip("domain", r.category)} <span class="faint small">${esc(r.severity)}</span>`,
        `<span class="small">${esc(r.inspector)} · <b>${esc(r.overall_grade ?? "–")}</b></span>${opts.highlightInspector && r.inspector === opts.highlightInspector ? " " + C.chip("model", "from " + r.inspector.split("_").pop()) : ""}`,
        `<span class="small">${esc(trunc(r.description, 220))}</span>`,
        `<span class="small muted">${esc(trunc(r.recommendation, 160))}</span>`,
      ])
    );
  };

  /* findings as cards, for narrow columns where the full table gets cramped */
  C.findingCards = (rows, opts = {}) =>
    rows && rows.length
      ? `<div class="records">${rows
          .map((r) => {
            const mine = opts.highlightInspector && r.inspector === opts.highlightInspector;
            return `<div class="record ${mine ? "highlight" : ""}" style="--c:var(--c-domain)"><div class="meta">
      ${r.score != null ? `<span>distance ${r.score.toFixed(3)}</span>` : ""}${C.chip("domain", r.category)}<span>${esc(r.severity)}</span>
      <span>${esc(r.inspector)} · grade ${esc(r.overall_grade ?? "–")}</span>${mine ? C.chip("model", "logged by " + r.inspector.split("_").pop()) : ""}</div>
      <div class="body">${esc(trunc(r.description, 220))}</div>
      ${r.recommendation ? `<div class="small muted" style="margin-top:4px">→ ${esc(trunc(r.recommendation, 160))}</div>` : ""}</div>`;
          })
          .join("")}</div>`
      : C.empty(opts.empty || "No findings.");

  C.pager = (route) => {
    const i = ORDER.indexOf(route);
    const prev = i > 0 ? ORDER[i - 1] : null;
    const next = i < ORDER.length - 1 ? ORDER[i + 1] : null;
    const link = (r, cls, lbl) =>
      `<a class="${cls}" href="#/${r}"><span class="faint">${lbl}</span>${esc(TITLES[r])}</a>`;
    return `<nav class="pager">${prev !== null ? link(prev, "prev", "← previous") : ""}${next !== null ? link(next, "next", "next →") : ""}</nav>`;
  };

  /* --------------------------------------------------- runtime readiness */

  function notReady() {
    const h = state.health;
    if (h && h.ready) return "";
    const why = h ? h.error : "Waiting for the server…";
    return `<div class="notice"><b>The live panels need Oracle and Ollama.</b> ${esc(why || "")}
      <div class="small faint" style="margin-top:6px">Everything on this page still reads fine without them. Check the status pills at the top, then press <a href="#" data-reconnect>Reconnect</a>.</div></div>`;
  }

  /* -------------------------------------------------------------- jobs */

  const STEP_RENDER = {}; // key -> (data, step, job) => html, extended by pages

  function defaultStepData(data) {
    if (data == null) return "";
    if (typeof data === "string")
      return `<div class="code wrap"><pre><code>${esc(data)}</code></pre></div>`;
    return C.json(data);
  }

  function renderJob(job, ui) {
    const statusChip = {
      queued: C.chip("", "queued"),
      running: C.chip("model", "running"),
      done: C.chip("ok", "done"),
      error: C.chip("err", "error"),
    }[job.status];
    const head = `<div class="job-head"><span class="ttl">${esc(job.title)}</span>${statusChip}<span class="mono">${job.seconds ? job.seconds + " s" : ""}</span>
      ${job.status === "queued" ? `<span class="faint">waiting for the previous job to finish</span>` : ""}</div>`;
    const steps = job.steps
      .map((s) => {
        const open = ui.open.has(s.key);
        const custom = (ui.renderers && ui.renderers[s.key]) || STEP_RENDER[s.key];
        const body =
          open && s.data != null
            ? `<div class="step-body">${custom ? custom(s.data, s, job) : defaultStepData(s.data)}</div>`
            : "";
        const icon = { done: "✓", error: "!", skipped: "–" }[s.status] || "";
        return `<div class="step" data-status="${s.status}" data-key="${esc(s.key)}">
        <div class="step-row" data-toggle="${esc(s.key)}"><span class="st">${icon}</span>
          <div><div class="s-title">${esc(s.title)}</div>${s.detail ? `<div class="s-detail">${esc(s.detail)}</div>` : ""}</div>
          <span class="s-ms">${fmtMs(s.ms)}${s.data != null ? (open ? " ▾" : " ▸") : ""}</span></div>${body}</div>`;
      })
      .join("");
    const calls = job.llm_calls.length
      ? `<div class="llm-calls"><div class="small faint mono">LLM calls in this job (${job.llm_calls.length}) — open one to read the exact prompt and reply</div>
      ${job.llm_calls
        .map(
          (c, i) => `<details class="llm-call" data-call="${i}" ${ui.calls.has(i) ? "open" : ""}>
        <summary>${C.chip(c.who === "agent" ? "model" : "sdk", c.who === "agent" ? "agent LLM" : "OAMP LLM")}<span>${esc(c.purpose)}</span><span class="faint mono small" style="margin-left:auto">${fmtMs(c.ms)}</span></summary>
        <div class="inner">${c.messages.map((m) => `<div class="msg-role">${esc(m.role)}</div><div class="code wrap"><pre><code>${esc(m.content)}</code></pre></div>`).join("")}
        <div class="msg-role">reply</div><div class="code wrap"><pre><code>${esc(c.response)}</code></pre></div></div></details>`
        )
        .join("")}</div>`
      : "";
    const deltas = Object.keys(job.deltas || {}).length
      ? `<div class="deltas"><span class="small faint mono">rows written:</span>${Object.entries(
          job.deltas
        )
          .map(([t, n]) =>
            C.chip(t.endsWith("_LINK") ? "model" : "memory", `${t} ${n > 0 ? "+" : ""}${n}`)
          )
          .join("")}</div>`
      : "";
    const ev = Object.entries(job.events || {});
    const events = ev.length
      ? C.more(
          `OAMP operation events in this job (${ev.reduce((a, [, n]) => a + n, 0)})`,
          `<div class="chips">${ev
            .sort((a, b) => b[1] - a[1])
            .map(([k, n]) => C.chip("sdk", `${k} ×${n}`))
            .join("")}</div>`
        )
      : "";
    const err = job.status === "error" ? C.error(job.error) : "";
    return head + `<div class="steps">${steps}</div>` + deltas + calls + events + err;
  }

  /** Start a job (startPromise resolves to {id}) and render it into el until it ends. */
  async function runJob(startPromise, el, opts = {}) {
    const ui = {
      open: new Set(opts.open || []),
      calls: new Set(),
      autoOpen: new Set(opts.autoOpen || []),
      renderers: opts.renderers,
    };
    el.classList.add("job");
    el.innerHTML = `<div class="job-head"><span class="ttl">Starting…</span></div>`;
    let job;
    try {
      const started = await startPromise;
      job = { id: started.id };
    } catch (e) {
      el.innerHTML = C.error(e);
      if (opts.onError) opts.onError(e);
      return null;
    }
    el.addEventListener("click", (ev) => {
      const row = ev.target.closest("[data-toggle]");
      if (row) {
        const k = row.dataset.toggle;
        ui.open.has(k) ? ui.open.delete(k) : ui.open.add(k);
        paint();
      }
    });
    el.addEventListener(
      "toggle",
      (ev) => {
        const d = ev.target.closest && ev.target.closest("[data-call]");
        if (d) {
          const i = +d.dataset.call;
          d.open ? ui.calls.add(i) : ui.calls.delete(i);
        }
      },
      true
    );
    let last = null;
    function paint() {
      if (last) {
        el.innerHTML = renderJob(last, ui);
        bindZoom(el);
      }
    }
    while (true) {
      try {
        last = await api.get("jobs/" + job.id);
      } catch (e) {
        el.innerHTML = C.error(e);
        return null;
      }
      for (const s of last.steps) {
        if (s.status === "done" && ui.autoOpen.has(s.key)) {
          ui.open.add(s.key);
          ui.autoOpen.delete(s.key);
        }
      }
      if (document.body.contains(el)) paint();
      if (opts.onUpdate) opts.onUpdate(last);
      if (last.status === "done" || last.status === "error") break;
      await new Promise((r) => setTimeout(r, 700));
    }
    refreshJobs();
    renderRunBox();
    if (state.drawerOpen) Drawer.load();
    if (last.status === "done" && opts.onDone) opts.onDone(last);
    if (last.status === "error" && opts.onError) opts.onError(new Error(last.error));
    return last;
  }

  async function refreshJobs() {
    try {
      const j = await api.get("jobs");
      state.jobs = j.active;
      renderTopbar();
    } catch (e) {
      /* server restarting */
    }
  }

  /* ----------------------------------------------------- lab steps */

  // Steps whose repetition would fail or mean nothing in the same run.
  const ONCE = new Set(["threads", "cleanup"]);

  C.trace = (t) => `<div class="trace">${(t.trace || [])
    .map((r) =>
      r.kind === "call"
        ? `<div class="t-row"><span class="t-kind call">MODEL → TOOL</span><div class="t-body">${esc(r.name)}(${esc(JSON.stringify(r.args))})</div></div>`
        : `<div class="t-row"><span class="t-kind result">TOOL → MODEL</span><div class="t-body">${esc(r.name)}: ${esc(r.content)}</div></div>`
    )
    .join("")}
    <div class="t-row"><span class="t-kind">FINAL ANSWER</span><div class="answer">${esc(t.answer)}</div></div></div>`;
  C.checks = (obj, labels) =>
    `<div class="checks">${Object.entries(labels)
      .map(([k, lbl]) => C.chip(obj[k] ? "ok" : "err", `${obj[k] ? "✓" : "✗"} ${lbl}`))
      .join("")}</div>`;

  /** A step's live panel: the stored result for this run, and a button that runs it (and its prerequisites). */
  async function stepPanel(el, key, opts = {}) {
    if (!state.health || !state.health.ready) {
      el.innerHTML = notReady();
      return;
    }
    let st;
    try {
      st = await api.get("state");
      state.lab = st;
    } catch (e) {
      el.innerHTML = C.error(e);
      return;
    }
    const res = st.results[key];
    const render = (data) => (STEP_RENDER[key] ? STEP_RENDER[key](data) : C.json(data));
    const once = ONCE.has(key) && st.done.includes(key);
    const needs = (st.steps.find((s) => s.key === key) || {}).needs || [];
    el.innerHTML = `<div class="row">
        <button class="btn ${res ? "" : "primary"}" data-run-step ${once || st.cleaned ? "disabled" : ""}>${res ? "Run again" : opts.label || "Run this step"}</button>
        <span class="small faint">${once ? "Done in this run — start a New run to repeat it." : st.cleaned && key !== "cleanup" ? "This run was cleaned up — start a New run." : opts.hint || (needs.length ? "Runs any earlier step it needs first." : "")}</span></div>
      <div class="step-result">${res ? render(res) : ""}</div><div class="step-job"></div>`;
    if (res && opts.onResult) opts.onResult(res);
    $("[data-run-step]", el).onclick = (ev) => {
      ev.target.disabled = true;
      $(".step-result", el).innerHTML = "";
      runJob(api.post("steps/" + key), $(".step-job", el), {
        autoOpen: [key],
        onDone: (job) => {
          const s = job.steps.find((x) => x.key === key);
          if (s && opts.onResult) opts.onResult(s.data);
          ev.target.disabled = false;
          ev.target.textContent = "Run again";
        },
        onError: () => {
          ev.target.disabled = false;
        },
      });
    };
  }

  /* -------------------------------------------------------------- shell */

  function renderSidebar() {
    const r = state.route;
    $("#sidebar").innerHTML = `
      <div class="brand"><div class="brand-mark"><svg width="20" height="20" viewBox="0 0 32 32"><path d="M8 12h14v10a4 4 0 0 1-4 4h-6a4 4 0 0 1-4-4z M22 14h2a3 3 0 0 1 0 6h-2" fill="none" stroke="#e7a033" stroke-width="2.3" stroke-linejoin="round" stroke-linecap="round"/><path d="M12 5c-1 1.5 1 2.5 0 4M16 5c-1 1.5 1 2.5 0 4" fill="none" stroke="#25b3a3" stroke-width="1.8" stroke-linecap="round"/></svg></div>
        <div><div class="brand-name">Inventory handover</div><div class="brand-sub">context + memory engineering</div></div></div>
      <nav class="nav">${NAV.map(
        (g) =>
          `<div class="nav-group">${g.group}</div>${g.items
            .map(
              ([route, title, num]) =>
                `<a href="#/${route}" class="${route === r ? "active" : ""}"><span class="num">${num}</span><span>${esc(title)}</span></a>`
            )
            .join("")}`
      ).join("")}</nav>
      <div class="nav-group" style="margin-top:22px">Notebook</div>
      <div class="small faint" style="padding:0 10px">Companion to the notebook <a class="mono" style="overflow-wrap:anywhere" href="https://github.com/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/inventory_handover/inventory_handover_agent_memory_oci.ipynb" target="_blank" rel="noopener">inventory_handover_agent_memory_oci.ipynb</a>. Each page runs the notebook's own code: OAMP 26.8, Oracle AI Database and Grok on OCI Generative AI.</div>
      <div id="run-box" style="padding:12px 10px 0"></div>`;
    renderRunBox();
  }

  /* the lab run: one RUN_ID, like a fresh notebook kernel */
  async function renderRunBox() {
    const box = document.getElementById("run-box");
    if (!box) return;
    if (!state.health || !state.health.ready) {
      box.innerHTML = "";
      return;
    }
    try {
      const st = await api.get("state");
      state.lab = st;
      box.innerHTML = `<div class="nav-group" style="padding:0;margin:0 0 6px">Lab run</div>
        <div class="small"><span class="mono">${esc(st.run_id)}</span> · ${st.done.length}/${st.steps.length} steps${st.cleaned ? " · cleaned up" : ""}</div>
        <button class="btn small" style="margin-top:8px" data-new-run>New run</button>`;
    } catch (e) {
      box.innerHTML = "";
    }
  }

  function renderTopbar() {
    const h = state.health;
    const dbOk = h && h.db && h.db.ok,
      onnxOk = h && h.onnx && h.onnx.ok,
      llmOk = h && h.ready && h.oci && h.oci.configured;
    const busy = state.jobs && state.jobs.length;
    $("#topbar").innerHTML = `
      <button class="pill menu-btn" data-menu>☰ Pages</button>
      <span class="crumb">${esc(state.route === "" ? "overview" : state.route)}</span>
      ${busy ? `<span class="pill" title="A job is running"><span class="dot busy"></span>${esc(trunc(state.jobs[0].title, 46))}</span>` : ""}
      <span class="pill" data-status><span class="dot ${h ? (dbOk ? "ok" : "err") : ""}"></span>Oracle</span>
      <span class="pill" data-status><span class="dot ${h ? (onnxOk ? "ok" : "err") : ""}"></span>ONNX</span>
      <span class="pill" data-status><span class="dot ${h ? (llmOk ? "ok" : "err") : ""}"></span>${esc(h && h.oci ? h.oci.model : "OCI GenAI")}</span>
      <button class="pill" data-theme-toggle title="Switch theme">${document.documentElement.dataset.theme === "dark" ? "☀ Light" : "☾ Dark"}</button>`;
  }

  function showStatus() {
    const h = state.health || {};
    const row = (k, ok, v) =>
      `<div class="status-item"><div class="k"><span class="dot ${ok ? "ok" : "err"}"></span>${k}</div><div class="v">${v}</div></div>`;
    $("#modal").innerHTML = `<div class="modal-card" style="max-width:760px">
      <h2 style="margin-top:0">Runtime status</h2>
      <div class="status-grid">
        ${row("Oracle AI Database", h.db && h.db.ok, `<span class="mono">${esc(h.db ? h.db.user + "@" + h.db.dsn : "")}</span><br><span class="small faint">${esc((h.db && (h.db.version || h.db.error)) || (h.db && !h.db.password_set ? "DBPASSWORD is not set" : ""))}</span>`)}
        ${row("In-database ONNX model", h.onnx && h.onnx.ok, `<span class="mono">${esc(h.onnx ? h.onnx.model : "")}</span>`)}
        ${row("OCI Generative AI", h.ready && h.oci && h.oci.configured, `<span class="mono">${esc(h.oci ? h.oci.model + " · " + h.oci.region : "")}</span><br><span class="small faint">${esc(h.oci ? h.oci.auth : "")}</span>`)}
        ${row(
          "Appbook memory store",
          h.ready,
          `<span class="mono">${esc(h.store || "")}_*</span> — the notebook's <span class="mono">ZH_INVENTORY_*</span> tables are never touched<br><span class="small faint">${esc(
            Object.entries(h.versions || {})
              .map(([k, v]) => k + " " + v)
              .join(" · ")
          )}</span>`
        )}
      </div>
      ${h.error && !h.ready ? `<p style="margin-top:12px">${C.error(h.error)}</p>` : ""}
      <div class="row" style="margin-top:14px"><button class="btn primary" data-reconnect>Reconnect</button><button class="btn" data-close>Close</button></div></div>`;
    $("#modal").hidden = false;
  }

  async function pollHealth() {
    try {
      const wasReady = state.health && state.health.ready;
      state.health = await api.get("health");
      state.jobs = state.health.jobs || [];
      if (!wasReady && state.health.ready && state.route !== null) route(); // live panels can now load
    } catch (e) {
      state.health = { ready: false, error: "The appbook server is not answering: " + e.message };
    }
    renderTopbar();
    setTimeout(pollHealth, state.health && state.health.ready ? 10000 : 3000);
  }

  function bindZoom(root) {
    $$("[data-zoom]", root).forEach((f) => {
      f.onclick = () => {
        $("#modal").innerHTML =
          `<div class="modal-card"><img src="${esc(f.dataset.zoom)}" alt=""><div class="row" style="margin-top:10px"><button class="btn" data-close>Close</button></div></div>`;
        $("#modal").hidden = false;
      };
    });
  }

  function route() {
    const r = (location.hash || "#/").replace(/^#\/?/, "").split("?")[0];
    state.route = pages[r] ? r : "";
    renderSidebar();
    renderTopbar();
    $("#sidebar").classList.remove("open");
    const page = pages[state.route];
    const stage = $("#stage");
    document.title = `${TITLES[state.route] || "Inventory handover"} · Inventory handover`;
    document.documentElement.style.setProperty("--accent", page.accent || "var(--c-memory)");
    stage.innerHTML = "";
    try {
      page.render(stage, {
        api,
        C,
        esc,
        runJob,
        notReady,
        ready: !!(state.health && state.health.ready),
        health: state.health,
      });
    } catch (e) {
      stage.innerHTML = C.error(e);
    }
    stage.insertAdjacentHTML("beforeend", C.pager(state.route));
    bindZoom(stage);
    if (state.lastRoute !== state.route) {
      window.scrollTo(0, 0);
      stage.focus({ preventScroll: true });
    }
    state.lastRoute = state.route;
  }

  /* ------------------------------------------------------- Data Explorer */

  const Drawer = {
    async load() {
      const body = $("#drawer-body");
      if (!state.health || !state.health.ready) {
        body.innerHTML = `<div>${notReady()}</div>`;
        return;
      }
      let info;
      try {
        info = await api.get("explorer/tables");
      } catch (e) {
        body.innerHTML = C.error(e);
        return;
      }
      if (!state.drawerTable && info.tables.length)
        state.drawerTable = (info.tables.find((t) => t.short === "MEMORY") || info.tables[0]).table;
      const groups = [
        ["Episodic", ["THREAD", "MESSAGE", "THREAD_SUMMARY"]],
        ["Semantic + procedural", ["MEMORY", "MEMORY_LINK"]],
        ["Retrieval + other", ["RECORD_CHUNKS", "DOCUMENT", "ACTOR_PROFILE"]],
      ];
      const list = groups
        .map(
          ([g, shorts]) =>
            `<div class="grp">${g}</div>` +
            info.tables
              .filter((t) => shorts.includes(t.short))
              .map(
                (t) =>
                  `<button data-table="${esc(t.table)}" class="${t.table === state.drawerTable ? "on" : ""}" title="${esc(t.purpose)}"><span>${esc(t.table)}</span><span>${t.rows}</span></button>`
              )
              .join("")
        )
        .join("");
      const activity = info.activity.length
        ? `<div class="activity"><div class="grp">Recent activity</div>${info.activity
            .slice(0, 8)
            .map(
              (a) =>
                `<div>${esc(a.status === "done" ? "✓" : a.status)} ${esc(trunc(a.title, 40))}${
                  Object.keys(a.deltas || {}).length
                    ? " · " +
                      Object.entries(a.deltas)
                        .map(([t, n]) => `${t.replace(state.health.store + "_", "")} +${n}`)
                        .join(", ")
                    : ""
                }</div>`
            )
            .join("")}</div>`
        : "";
      body.innerHTML = `<div><div class="tbl-list">${list}</div>${activity}</div><div id="drawer-rows"></div>`;
      $$("[data-table]", body).forEach(
        (b) =>
          (b.onclick = () => {
            state.drawerTable = b.dataset.table;
            state.drawerFilter = null;
            Drawer.load();
          })
      );
      const t = info.tables.find((x) => x.table === state.drawerTable);
      if (t) Drawer.rows(t);
    },
    async rows(t, offset = 0) {
      const el = $("#drawer-rows");
      const f = state.drawerFilter || {};
      el.innerHTML = `<div class="small faint">Loading ${esc(t.table)}…</div>`;
      let data;
      try {
        data = await api.get("explorer/rows", {
          table: t.table,
          limit: 25,
          offset,
          filter_column: f.col,
          filter_value: f.val,
        });
      } catch (e) {
        el.innerHTML = C.error(e);
        return;
      }
      const filterUi = t.filters.length
        ? `<div class="row" style="margin-bottom:8px">
        <label style="flex:0 0 160px">filter column<select data-fcol><option value="">(none)</option>${t.filters.map((c) => `<option ${f.col === c ? "selected" : ""}>${c}</option>`).join("")}</select></label>
        <label>equals<input type="text" data-fval value="${esc(f.val || "")}" placeholder="e.g. Harbor Bridge"></label>
        <button class="btn small" data-fapply>Apply</button></div>`
        : "";
      const head = `<div class="small" style="margin-bottom:6px"><b class="mono">${esc(t.table)}</b> · ${esc(t.purpose)} · <span class="faint">${data.total} row(s); read-only; vectors stay in the database; text cut to 300 characters</span></div>`;
      const table = data.rows.length
        ? C.table(
            data.columns.map(esc),
            data.rows.map((r) =>
              data.columns.map((c) => {
                const v = r[c];
                const s = v && typeof v === "object" ? JSON.stringify(v) : v;
                return `<span class="small ${typeof v === "number" ? "mono" : ""}">${esc(trunc(s, 160))}</span>`;
              })
            )
          )
        : C.empty("No rows yet.");
      const pager =
        data.total > data.limit
          ? `<div class="row"><button class="btn small" data-prev ${offset <= 0 ? "disabled" : ""}>← newer</button><span class="small faint">${offset + 1}–${Math.min(offset + data.limit, data.total)} of ${data.total}</span><button class="btn small" data-next ${offset + data.limit >= data.total ? "disabled" : ""}>older →</button></div>`
          : "";
      el.innerHTML = head + filterUi + table + pager;
      const apply = $("[data-fapply]", el);
      if (apply)
        apply.onclick = () => {
          state.drawerFilter = {
            col: $("[data-fcol]", el).value || null,
            val: $("[data-fval]", el).value,
          };
          Drawer.rows(t, 0);
        };
      const prev = $("[data-prev]", el),
        next = $("[data-next]", el);
      if (prev) prev.onclick = () => Drawer.rows(t, Math.max(0, offset - data.limit));
      if (next) next.onclick = () => Drawer.rows(t, offset + data.limit);
    },
    toggle(open) {
      const d = $("#drawer");
      state.drawerOpen = open ?? d.dataset.open !== "true";
      d.dataset.open = String(state.drawerOpen);
      $(".chev", d).textContent = state.drawerOpen ? "▾ close" : "▴ open";
      if (state.drawerOpen) Drawer.load();
    },
    open(tableShort, filter) {
      if (state.health && state.health.store)
        state.drawerTable = state.health.store + "_" + tableShort;
      state.drawerFilter = filter || null;
      Drawer.toggle(true);
    },
  };

  /* --------------------------------------------------------------- boot */

  function boot() {
    $("#drawer").innerHTML =
      `<div class="drawer-head" data-drawer><span class="ttl">Data Explorer</span>
      <span class="faint">every table this appbook writes, read-only</span><span class="chev">▴ open</span></div><div class="drawer-body" id="drawer-body"></div>`;
    document.addEventListener("click", (ev) => {
      const t = ev.target;
      if (t.closest("[data-drawer]")) Drawer.toggle();
      if (t.closest("[data-status]")) showStatus();
      if (t.closest("[data-close]") || t.id === "modal") $("#modal").hidden = true;
      if (t.closest("[data-menu]")) $("#sidebar").classList.toggle("open");
      const ex = t.closest("[data-explore]");
      if (ex) {
        ev.preventDefault();
        const [tbl, col, val] = ex.dataset.explore.split("|");
        Drawer.open(tbl, col ? { col, val } : null);
      }
      if (t.closest("[data-theme-toggle]")) {
        const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        try {
          localStorage.setItem("inventory-theme", next);
        } catch (e) {}
        renderTopbar();
      }
      if (t.closest("[data-new-run]")) {
        api
          .post("new-run")
          .then(() => {
            alertToast("Started a new lab run");
            route();
          })
          .catch((e) => alertToast(e.message));
      }
      if (t.closest("[data-reconnect]")) {
        ev.preventDefault();
        $("#modal").hidden = true;
        state.health = { ...(state.health || {}), ready: false, error: "Reconnecting…" };
        renderTopbar();
        api
          .post("reconnect")
          .then(() => pollHealthOnce())
          .catch((e) => alertToast(e.message));
      }
    });
    window.addEventListener("hashchange", route);
    pollHealth().then(() => route());
  }
  async function pollHealthOnce() {
    try {
      state.health = await api.get("health");
    } catch (e) {}
    renderTopbar();
    route();
  }
  function alertToast(text) {
    const t = $("#toast");
    t.textContent = text;
    t.hidden = false;
    clearTimeout(alertToast.timer);
    alertToast.timer = setTimeout(() => (t.hidden = true), 6000);
  }

  return {
    boot,
    page: (r, def) => (pages[r] = def),
    api,
    C,
    esc,
    trunc,
    fmtMs,
    runJob,
    notReady,
    STEP_RENDER,
    Drawer,
    state,
    toast: alertToast,
    $,
    $$,
    renderRunBox,
    stepPanel,
  };
})();
