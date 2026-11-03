/* Overview, Part 1 (Oracle setup) and Part 2 (the embedder and the SDK). Diagram-first. */

(() => {
  const { C, esc, api, $, $$ } = App;
  const F = D.F;

  /* ================================================================ overview */

  App.page("", {
    accent: "var(--c-memory)",
    render(el, ctx) {
      const prefix = (ctx.health && ctx.health.prefix) || "CITYAPP_";
      const model = (ctx.health && ctx.health.ollama && ctx.health.ollama.model) || "llama3.2";
      el.innerHTML = `
        <p class="eyebrow">CityOps Copilot · agent memory</p>
        <h1>An inspection copilot that remembers</h1>
        <p class="lede">A field assistant for the people who inspect a city's bridges, substations and pipelines. It suggests a diagnosis —
        and brings back what <em>other</em> inspectors already found on the same asset, because it remembers.</p>
        <div id="ov-status"></div>

        <h2>The whole system on one page</h2>
        ${C.fig(
          F.architecture(),
          `Three layers on one database. <b style="color:var(--d-req)">Amber</b>: the request and the answer.
          <b style="color:var(--d-write)">Salmon</b>: the write path that grows memory. <b style="color:var(--d-read)">Blue</b>: the read path that brings it back.`
        )}

        <h2>Why a copilot needs memory</h2>
        <div class="grid3">
          <div class="card state-card k-model"><div class="kicker">Gap 1</div><h3>The model is stateless</h3>
            <p class="muted small">Every call starts blank. It knows corrosion in general — nothing about Pier 2 of Harbor Bridge.</p></div>
          <div class="card state-card k-domain"><div class="kicker">Gap 2</div><h3>Knowledge is scattered</h3>
            <p class="muted small">Old reports, structured findings, and lessons that only live in inspectors' heads.</p></div>
          <div class="card state-card k-memory"><div class="kicker">Gap 3</div><h3>Handoffs depend on people</h3>
            <p class="muted small">A new inspector learns the asset's past only if someone remembers to brief them.</p></div>
        </div>
        ${C.term(
          "agent memory",
          `<p>State an agent keeps <b>across calls and conversations</b> — written by its own interactions, read back by relevance,
          and <b>scoped</b> so the right people (and only they) see it.</p>`
        )}
        ${C.more(
          "What agent memory is not",
          C.table(
            ["Not this…", "…because"],
            [
              [
                "<b>The context window</b>",
                "That is one call's working space. Memory decides what goes into it, and survives the call.",
              ],
              [
                "<b>RAG over documents</b>",
                "RAG reads what someone loaded. Memory is mostly formed by the agent as it works. (This copilot uses both.)",
              ],
              [
                "<b>Fine-tuning</b>",
                "That changes weights for everyone. Memory is data: per asset, per inspector, inspectable, deletable.",
              ],
            ],
            "prose-table"
          )
        )}

        <h2>Two kinds of state</h2>
        ${C.fig(
          F.state(),
          `<b>Domain data</b> is the system of record: the copilot reads it and never invents it; inspectors add to it on purpose.
          <b>Memory</b> is what the copilot forms from conversations, and it grows by itself on every turn.`
        )}

        <h2>Every turn: read, reason, write</h2>
        ${C.fig(F.loop(), `The last step is the point: writing the turn back is what makes the <em>next</em> turn — possibly by another inspector — better informed.`)}

        <h2>How the notebook builds it</h2>
        ${C.fig(F.roadmap(), `Parts 3–5 each build one component and verify it alone; Part 6 assembles them. Click a box to open that Part.`)}

        <h2>Using this appbook</h2>
        <div class="grid2">
          <div class="card"><h3 style="margin-top:0">Read the diagram, then try it</h3><p class="small muted">Each <i>Try it</i> panel runs the notebook's own code — same SQL, SDK calls and prompts — against Oracle and <span class="mono">${esc(model)}</span>.</p></div>
          <div class="card"><h3 style="margin-top:0">Open the steps</h3><p class="small muted">Model calls run as jobs with numbered steps. Open an LLM call to read the exact prompt, including the ones the SDK writes for itself.</p></div>
          <div class="card"><h3 style="margin-top:0">Look at the tables</h3><p class="small muted">The <a href="#" data-explore="MEMORY">Data Explorer</a> at the bottom shows every row this appbook writes, read-only.</p></div>
          <div class="card"><h3 style="margin-top:0">Your notebook is safe</h3><p class="small muted">The appbook writes only <span class="mono">${esc(prefix)}*</span> tables; the notebook's <span class="mono">CITY_*</span> tables are never touched.</p></div>
        </div>
        ${C.more(
          "Glossary",
          `<dl class="glossary">
          <dt>thread</dt><dd>One conversation with a scope (<span class="mono">user_id</span>, <span class="mono">agent_id</span>, <span class="mono">thread_id</span>). The copilot uses one per inspector per asset.</dd>
          <dt>message</dt><dd>One turn of a thread, stored verbatim. Episodic memory: what was said.</dd>
          <dt>memory record</dt><dd>A short, standalone statement the extractor distils: fact, preference, guideline or memory.</dd>
          <dt>extraction</dt><dd>The SDK's own LLM call that turns messages into records. You don't write its prompt.</dd>
          <dt>context card</dt><dd>A prompt-ready XML summary of one thread: topics, summary, relevant records, recent messages.</dd>
          <dt>scope / principal</dt><dd>Who a record belongs to. Searches match it exactly, as SQL predicates.</dd>
          <dt>embedding</dt><dd>384 numbers that place a text in "meaning space".</dd>
          <dt>cosine distance</dt><dd>0 = same direction, ≈1 = unrelated. <span class="mono">VECTOR_DISTANCE(…, COSINE)</span> computes it in SQL.</dd>
          <dt>HNSW index</dt><dd>A layered graph of nearest neighbours: find similar vectors without scanning every row.</dd>
        </dl>`
        )}
        ${C.takeaway(`<p>Memory turns a stateless model into a colleague with a record: it keeps what happened, distils what is worth keeping,
          and brings back only what matters for this asset and this inspector.</p>`)}`;
      if (ctx.ready) loadStatus($("#ov-status", el), ctx);
      else $("#ov-status", el).innerHTML = ctx.notReady();
    },
  });

  async function loadStatus(box, ctx) {
    try {
      const o = await api.get("overview");
      const h = ctx.health;
      const t = (n) => o.tables[o.prefix + n] ?? 0;
      box.innerHTML = `<div class="status-grid">
        <div class="status-item"><div class="k"><span class="dot ok"></span>Oracle AI Database</div><div class="v mono small">${esc(h.db.user)}@${esc(h.db.dsn)}</div></div>
        <div class="status-item"><div class="k"><span class="dot ok"></span>Embeddings in the database</div><div class="v mono small">${esc(h.onnx.model)}</div></div>
        <div class="status-item"><div class="k"><span class="dot ${h.ollama.ok ? "ok" : "err"}"></span>Local model</div><div class="v mono small">${esc(h.ollama.model)}</div></div>
        <div class="status-item"><div class="k">This workspace</div><div class="v small">${t("ASSET")} assets · ${t("INSPECTION_FINDING")} findings · ${o.threads} threads · ${t("MESSAGE")} messages · ${t("MEMORY")} memory records</div></div>
      </div>`;
    } catch (e) {
      box.innerHTML = C.error(e);
    }
  }

  /* ================================================================ Part 1 */

  App.page("part1", {
    accent: "var(--c-domain)",
    render(el, ctx) {
      const prefix = (ctx.health && ctx.health.prefix) || "CITYAPP_";
      el.innerHTML = `
        <p class="eyebrow">Part 1 · Oracle setup</p>
        <h1>One database for data and memory</h1>
        <p class="lede">The asset registry, the findings and their vectors, and the SDK's threads, messages and records all live in one
        Oracle AI Database, behind one connection.</p>
        ${C.learn([
          ["See", "why memory belongs next to the data"],
          ["Meet", "the tables you create and the ones the SDK creates"],
          ["Try", "every table live, and a reset"],
        ])}

        <h2>Why one converged engine</h2>
        ${C.fig(
          F.converged(),
          `Memory is searched <b>by meaning</b> and filtered <b>by who and what</b>. In one engine that is one SQL statement —
          so the access rules (Part 5) apply in the same query as the vector ranking, not afterwards.`
        )}

        <h2>Who creates which table</h2>
        ${C.fig(
          F.tables("CITY_"),
          `You write the DDL for the two domain tables; the SDK creates and owns the memory tables when it starts.
          The appbook keeps its own copies under <span class="mono">${esc(prefix)}</span>.`
        )}
        ${C.more(
          "See the connection code",
          C.code(`import oracledb
from dotenv import load_dotenv

load_dotenv(".env", override=False)

DB_USER     = os.getenv("DBUSER", "prism")
DB_PASSWORD = os.getenv("DBPASSWORD", os.getenv("PASSWORD", "CHANGE_ME"))
DB_DSN      = os.getenv("DB_DSN", "localhost:1522/FREEPDB1")   # host:port/service

oracledb.defaults.fetch_lobs = False   # CLOBs come back as str, JSON as dict/list
vector_conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)`) +
            `<p class="small muted">The appbook reads the same <span class="mono">.env</span>, and uses a small connection pool instead of one connection.</p>`
        )}

        ${C.tryPanel("p1-try", "The appbook's tables, live", "read-only, plus a reset", `<div id="p1-live"></div>`)}
        ${C.takeaway(`<p>Memory is data: ordinary tables you can query, join, secure and back up — sitting next to the data it is about.</p>`)}`;
      const live = $("#p1-live", el);
      if (!ctx.ready) {
        live.innerHTML = ctx.notReady();
        return;
      }
      loadTables(live, prefix);
    },
  });

  async function loadTables(live, prefix) {
    live.innerHTML = `<div class="small faint">Loading…</div>`;
    let info;
    try {
      info = await api.get("explorer/tables");
    } catch (e) {
      live.innerHTML = C.error(e);
      return;
    }
    const h = App.state.health;
    live.innerHTML = `
      <p class="small">Connected as <b class="mono">${esc(h.db.user)}</b> to <span class="mono">${esc(h.db.dsn)}</span>${h.db.version ? ` · Oracle ${esc(h.db.version)}` : ""}.</p>
      ${C.table(
        ["Table", "Rows", "What it is", ""],
        info.tables.map((t) => [
          `<span class="mono">${esc(t.table)}</span>`,
          `<span class="mono">${t.rows}</span>`,
          `<span class="small">${esc(t.purpose)}</span>`,
          `<a href="#" class="small" data-explore="${esc(t.short)}">browse</a>`,
        ])
      )}
      <div class="row"><button class="btn danger" data-reset>Reset the appbook's workspace…</button>
      <span class="small faint">Drops and rebuilds only <span class="mono">${esc(prefix)}*</span>, then reloads the assets and the first findings.</span></div>
      <div id="p1-job"></div>`;
    const btn = $("[data-reset]", live);
    btn.onclick = () => {
      if (!btn.dataset.armed) {
        btn.dataset.armed = "1";
        btn.textContent = "Click again to drop and rebuild";
        return;
      }
      btn.disabled = true;
      App.runJob(api.post("reset"), $("#p1-job", live), {
        onDone: () => setTimeout(() => loadTables(live, prefix), 300),
      });
    };
  }

  /* ================================================================ Part 2 */

  App.page("part2", {
    accent: "var(--c-sdk)",
    render(el, ctx) {
      const h = ctx.health || {};
      const model = (h.onnx && h.onnx.model) || "ALL_MINILM_L12_V2";
      const llm = (h.ollama && h.ollama.model) || "llama3.2";
      el.innerHTML = `
        <p class="eyebrow">Part 2 · The embedder and the SDK</p>
        <h1>Teaching the database to compare meanings</h1>
        <p class="lede">To remember by meaning, text becomes vectors — inside Oracle. Then the memory client gets three things from you:
        a connection, an embedder and an LLM of its own.</p>
        ${C.learn([
          ["See", "text → vector → distance, all in the database"],
          ["Meet", "the IEmbedder bridge and OracleAgentMemory"],
          ["Try", "a live meaning map of your own sentences"],
        ])}

        <h2>Text becomes a vector inside Oracle</h2>
        ${C.fig(
          F.embedPipeline(model),
          `<span class="mono">VECTOR_EMBEDDING()</span> runs the loaded ONNX model in SQL: no API key, no per-call cost,
          and the same model for every stored vector and every query, so they are comparable.`
        )}
        ${C.term(
          "cosine distance",
          `<p>The angle between two vectors: <b>0</b> means the same direction, around <b>1</b> means unrelated.
          <span class="mono">VECTOR_DISTANCE(a, b, COSINE)</span> ranks every memory and finding search in this notebook.</p>`
        )}

        ${C.tryPanel(
          "p2-try",
          "Embed and compare",
          "VECTOR_EMBEDDING() in Oracle",
          `
          <div class="form">
            <div class="grid3">
              <label>sentence A<textarea data-t rows="2">corrosion on bearing assembly</textarea></label>
              <label>sentence B<textarea data-t rows="2">rust on the pier bearings</textarea></label>
              <label>sentence C<textarea data-t rows="2">the substation transformer hums loudly</textarea></label>
            </div>
            <div class="row"><button class="btn primary" data-embed>Embed in Oracle</button><span class="small faint">Each sentence becomes 384 numbers; the map places them by distance.</span></div>
          </div>
          <div id="p2-out"></div>`
        )}

        <h2>Wiring the memory client</h2>
        ${C.fig(
          F.sdkWiring(llm, "CITY_"),
          `One constructor call. The SDK's <b>own</b> LLM does its background work — extracting records and summarising threads —
          separately from the agent LLM that answers the inspector. Here both are <span class="mono">${esc(llm)}</span>.`
        )}
        ${C.more(
          "See the code",
          C.code(`class OracleONNXEmbedder(IEmbedder):
    """Bridges Oracle's in-database ONNX embeddings to the SDK's IEmbedder."""

    def __init__(self, conn, model_name: str = ONNX_MODEL):
        self.provider = OracleEmbeddings(conn=conn, params={"provider": "database", "model": model_name})

    def embed(self, texts, *, is_query=False) -> np.ndarray:
        return np.asarray(self.provider.embed_documents(list(texts)), dtype=np.float32)

sdk_llm = Llm(model=f"openai/{OLLAMA_MODEL}", api_base=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")

memory = OracleAgentMemory(
    connection=vector_conn,
    embedder=OracleONNXEmbedder(vector_conn),
    llm=sdk_llm,
    extract_memories=True,                       # distil records on every add_messages()
    schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
    table_name_prefix="CITY_",
)`)
        )}
        ${C.takeaway(`<p>Embeddings give memory its sense of similarity; computing them in the database keeps text private and vectors consistent.
          The SDK then needs a connection, an embedder and an LLM — and manages its tables itself.</p>`)}`;
      const out = $("#p2-out", el);
      $("[data-embed]", el).onclick = async () => {
        if (!App.state.health || !App.state.health.ready) {
          out.innerHTML = ctx.notReady();
          return;
        }
        const texts = $$("[data-t]", el)
          .map((t) => t.value)
          .filter((t) => t.trim());
        out.innerHTML = `<div class="small faint" style="margin-top:10px">Embedding…</div>`;
        try {
          renderEmbeddings(out, await api.post("embed", { texts }));
        } catch (e) {
          out.innerHTML = C.error(e);
        }
      };
    },
  });

  function spark(vec) {
    const w = 384,
      hgt = 46,
      max = Math.max(...vec.map(Math.abs), 1e-6);
    const bars = vec
      .map((v, i) => {
        const y = (v / max) * (hgt / 2 - 1);
        return `<rect x="${i}" y="${(hgt / 2 - Math.max(y, 0)).toFixed(2)}" width="0.8" height="${Math.abs(y).toFixed(2)}" fill="${v >= 0 ? "var(--c-memory)" : "var(--c-model)"}"/>`;
      })
      .join("");
    return `<svg class="spark" viewBox="0 0 ${w} ${hgt}" preserveAspectRatio="none"><line x1="0" x2="${w}" y1="${hgt / 2}" y2="${hgt / 2}" stroke="var(--line-2)" stroke-width="0.5"/>${bars}</svg>`;
  }

  function renderEmbeddings(out, r) {
    const labels = r.texts.map((_, i) => String.fromCharCode(65 + i));
    const color = (d) => {
      const t = Math.max(0, Math.min(1, d / 0.9));
      return `hsl(${170 - t * 150} 65% ${62 - t * 10}%)`;
    };
    const pairs = [];
    for (let i = 0; i < r.texts.length; i++)
      for (let j = i + 1; j < r.texts.length; j++) pairs.push([i, j, r.distances[i][j]]);
    pairs.sort((a, b) => a[2] - b[2]);
    out.innerHTML = `
      ${r.texts.length > 1 ? F.meaningMap(labels, r.texts, r.distances) : ""}
      <p class="small" style="margin-top:6px">Shape <b class="mono">(${r.shape.join(", ")})</b> · <span class="mono">${esc(r.dtype)}</span> · ${r.ms} ms in the database</p>
      <div class="grid2">
        <div>${r.texts
          .map(
            (t, i) =>
              `<div class="small" style="margin-top:6px"><b>${labels[i]}</b> <span class="faint mono">[${r.vectors[
                i
              ]
                .slice(0, 4)
                .map((x) => x.toFixed(3))
                .join(", ")}, …]</span></div>${spark(r.vectors[i])}`
          )
          .join("")}</div>
        <div><div class="tbl-wrap"><table class="matrix"><thead><tr><th></th>${labels.map((l) => `<th>${l}</th>`).join("")}</tr></thead>
        <tbody>${r.distances.map((row, i) => `<tr><th>${labels[i]}</th>${row.map((d, j) => (i === j ? `<td class="faint">—</td>` : `<td class="cell" style="background:${color(d)}">${d.toFixed(3)}</td>`)).join("")}</tr>`).join("")}</tbody></table></div></div>
      </div>
      ${
        pairs.length
          ? C.watch(`<p>Closest: <b>${labels[pairs[0][0]]}–${labels[pairs[0][1]]}</b> (${pairs[0][2].toFixed(3)}). The two corrosion sentences share almost no words,
        yet sit far closer to each other than to the substation one. Edit a sentence and embed again.</p>`)
          : ""
      }`;
  }
})();
