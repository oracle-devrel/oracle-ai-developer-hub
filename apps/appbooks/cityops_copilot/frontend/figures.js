/* Diagrams: a small inline-SVG toolkit (layers, nodes, pills, arrows) and the
   appbook's figures. Colours come from CSS variables (--d-*), so every figure
   follows the light/dark theme. Arrow colours carry meaning everywhere:
   amber = request/response, salmon = write path, blue = read path,
   violet = model call, gold = data. */

const D = (() => {
  const esc = App.esc;

  /* ------------------------------------------------------------ toolkit */

  const ICON = {
    users:
      '<circle cx="9" cy="8" r="3.2"/><path d="M3 19c.6-3.3 3-5 6-5s5.4 1.7 6 5"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14.2c2.4.2 4.3 1.7 4.8 4.8"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.8v2.6M12 18.6v2.6M21.2 12h-2.6M5.4 12H2.8M18.5 5.5l-1.8 1.8M7.3 16.7l-1.8 1.8M18.5 18.5l-1.8-1.8M7.3 7.3 5.5 5.5"/>',
    book: '<path d="M3 5.5c3-1 6-1 9 1 3-2 6-2 9-1v13c-3-1-6-1-9 1-3-2-6-2-9-1z"/><path d="M12 6.5v13"/>',
    bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    db: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v13c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8v-13"/><path d="M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    cross: '<path d="M6 6l12 12M18 6 6 18"/>',
    search: '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5.5 5.5"/>',
    doc: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    bridge:
      '<path d="M2 18h20M4 18v-5M20 18v-5M2 11c4 0 6.5 3 10 3s6-3 10-3"/><path d="M8 18v-3.6M12 18v-4M16 18v-3.6"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
    sparkle:
      '<path d="M12 3v5M12 16v5M3 12h5M16 12h5M6.5 6.5l2.6 2.6M14.9 14.9l2.6 2.6M6.5 17.5l2.6-2.6M14.9 9.1l2.6-2.6"/>',
    dots: '<circle cx="5" cy="7" r="1.6"/><circle cx="12" cy="5" r="1.6"/><circle cx="19" cy="9" r="1.6"/><circle cx="7" cy="15" r="1.6"/><circle cx="14" cy="13" r="1.6"/><circle cx="17" cy="19" r="1.6"/>',
  };
  const KINDS = ["req", "write", "read", "model", "data", "muted", "ok", "err", "sdk"];

  const tw = (s, size = 12, mono = true) => String(s).length * size * (mono ? 0.6 : 0.54);

  function svg(w, h, body, { title = "", cls = "", min = 680 } = {}) {
    const markers = KINDS.map(
      (k) =>
        `<marker id="ah-${k}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0.5 L10 5 L0 9.5 z" class="ah ${k}"/></marker>`
    ).join("");
    return `<div class="dg-wrap ${cls}"><svg class="dg" viewBox="0 0 ${w} ${h}" style="min-width:${min}px" role="img" aria-label="${esc(title)}"><defs>${markers}</defs>${body}</svg></div>`;
  }

  const icon = (name, x, y, size = 20, cls = "") =>
    `<g class="dg-icon ${cls}" transform="translate(${x},${y}) scale(${size / 24})">${ICON[name] || ""}</g>`;

  function text(x, y, s, { cls = "", anchor = "start", size, weight } = {}) {
    const st = [size ? `font-size:${size}px` : "", weight ? `font-weight:${weight}` : ""]
      .filter(Boolean)
      .join(";");
    return `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}"${st ? ` style="${st}"` : ""}>${esc(s)}</text>`;
  }

  function layer(x, y, w, h, label, { kind = "", lcls = "" } = {}) {
    return (
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" class="layer ${kind}"/>` +
      (label
        ? text(x + 16, y + 21, String(label).toUpperCase(), { cls: `layer-lbl ${kind} ${lcls}` })
        : "")
    );
  }

  /** A card: icon + title + up to two sub lines. opts.id makes it addressable for live updates. */
  function node(x, y, w, h, { icon: ic, title, sub, sub2, kind = "", id, href, tsize } = {}) {
    const lines = [title, sub, sub2].filter((v) => v != null && v !== "").length;
    const tx = ic ? x + 44 : x + 16;
    const top = y + h / 2 - (lines === 1 ? -5 : lines === 2 ? 5 : 14);
    let out = `<g class="node ${kind}"${id ? ` id="${id}"` : ""}><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10"/>`;
    if (ic) out += icon(ic, x + 13, y + h / 2 - 10, 20);
    out += text(tx, top, title, { cls: "n-title", size: tsize });
    if (sub) out += text(tx, top + 18, sub, { cls: "n-sub" });
    if (sub2) out += text(tx, top + 34, sub2, { cls: "n-sub" });
    out += `</g>`;
    return href ? `<a href="${href}" class="dg-link">${out}</a>` : out;
  }

  function pill(x, y, s, { kind = "", size = 12, h = 28 } = {}) {
    const w = tw(s, size) + 24;
    return {
      w,
      svg: `<g class="pill ${kind}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${h / 2}"/>${text(x + w / 2, y + h / 2 + size * 0.36, s, { cls: "p-text", anchor: "middle", size })}</g>`,
    };
  }
  function pills(x, y, items, { gap = 8, size = 12, h = 28 } = {}) {
    let cx = x,
      out = "";
    for (const it of items) {
      const [s, kind] = Array.isArray(it) ? it : [it, ""];
      const p = pill(cx, y, s, { kind, size, h });
      out += p.svg;
      cx += p.w + gap;
    }
    return out;
  }

  /** A polyline arrow. pts = [[x,y],…]; label at [x,y] with anchor. */
  function arrow(
    pts,
    {
      kind = "muted",
      label,
      at,
      anchor = "middle",
      dashed = false,
      start = false,
      end = true,
      id,
      width,
    } = {}
  ) {
    const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
    let out =
      `<path d="${d}" class="arrow ${kind} ${dashed ? "dashed" : ""}"${id ? ` id="${id}"` : ""}${width ? ` style="stroke-width:${width}"` : ""}` +
      `${end ? ` marker-end="url(#ah-${kind})"` : ""}${start ? ` marker-start="url(#ah-${kind})"` : ""}/>`;
    if (label) {
      const [lx, ly] = at || [
        (pts[0][0] + pts[pts.length - 1][0]) / 2,
        (pts[0][1] + pts[pts.length - 1][1]) / 2 - 7,
      ];
      out += text(lx, ly, label, { cls: `a-lbl ${kind}`, anchor });
    }
    return out;
  }

  /** A titled container (a package or a database inside a layer). */
  function box(x, y, w, h, { title, ic, kind = "" } = {}) {
    return (
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" class="box ${kind}"/>` +
      (ic ? icon(ic, x + 14, y + 12, 18, `box-ic ${kind}`) : "") +
      (title
        ? text(x + (ic ? 42 : 16), y + 26, String(title).toUpperCase(), {
            cls: `box-title ${kind}`,
          })
        : "")
    );
  }

  /* ------------------------------------------------------------ figures */

  const F = {};

  /** Overview: the whole copilot as layers, after the Oracle architecture slide. */
  F.architecture = () => {
    let b = "";
    b += layer(10, 34, 700, 112, "Application layer");
    b += layer(10, 196, 186, 236, "Domain SQL", { kind: "data" });
    b += layer(206, 196, 504, 236, "Memory layer");
    b += layer(10, 470, 700, 170, "Data layer", { kind: "data" });
    b += layer(730, 34, 260, 606, "Model layer");
    // application
    b += node(26, 66, 160, 58, { icon: "users", title: "Inspector", sub: "narrative · asset" });
    b += node(262, 66, 190, 58, { icon: "gear", title: "call_copilot", sub: "one agent turn" });
    b += node(520, 66, 150, 58, { icon: "book", title: "Prompt", sub: "assembled per turn" });
    b += arrow(
      [
        [186, 95],
        [262, 95],
      ],
      { kind: "req", label: "narrative", at: [224, 87] }
    );
    b += arrow(
      [
        [452, 95],
        [520, 95],
      ],
      { kind: "req", label: "builds", at: [486, 87] }
    );
    b += arrow(
      [
        [670, 95],
        [752, 95],
      ],
      { kind: "req", label: "tokens in", at: [711, 87] }
    );
    b += arrow(
      [
        [864, 66],
        [864, 16],
        [357, 16],
        [357, 66],
      ],
      { kind: "req", label: "answer", at: [800, 11] }
    );
    // domain SQL
    b += node(24, 226, 158, 80, {
      icon: "search",
      title: "Plain SQL",
      sub: "asset lookup",
      sub2: "similar findings",
    });
    b += arrow(
      [
        [70, 124],
        [70, 226],
      ],
      { kind: "write", label: "log_finding", at: [76, 152], anchor: "start" }
    );
    b += arrow(
      [
        [274, 124],
        [274, 166],
        [160, 166],
        [160, 226],
      ],
      { kind: "read", label: "lookups", at: [216, 160] }
    );
    b += arrow(
      [
        [70, 306],
        [70, 500],
      ],
      { kind: "write", label: "insert", at: [76, 384], anchor: "start" }
    );
    b += arrow(
      [
        [160, 306],
        [160, 500],
      ],
      { kind: "read", label: "query", at: [154, 426], anchor: "end" }
    );
    // memory package
    b += box(222, 226, 472, 190, {
      title: "Oracle AI Agent Memory · SDK",
      ic: "layers",
      kind: "sdk",
    });
    b += text(240, 278, "WRITE PATH · retain, distil", { cls: "path-lbl write" });
    b += pills(240, 288, [
      ["add_messages", "write"],
      ["extraction", "write"],
      ["summary", "write"],
      ["add_memory", "write"],
    ]);
    b += text(240, 350, "READ PATH · recall, reuse", { cls: "path-lbl read" });
    b += pills(240, 360, [
      ["SearchScope", "read"],
      ["search_async", "read"],
      ["context card", "read"],
    ]);
    b += arrow(
      [
        [330, 124],
        [330, 226],
      ],
      { kind: "write", label: "messages", at: [336, 182], anchor: "start" }
    );
    b += arrow(
      [
        [410, 124],
        [410, 226],
      ],
      { kind: "read", label: "query + scope", at: [416, 182], anchor: "start" }
    );
    b += arrow(
      [
        [595, 226],
        [595, 124],
      ],
      { kind: "read", label: "context card", at: [601, 182], anchor: "start" }
    );
    // model
    b += node(752, 66, 224, 58, { icon: "bulb", title: "Agent LLM", sub: "llama3.2 · stateless" });
    b += node(752, 262, 224, 58, {
      icon: "bolt",
      title: "SDK LLM",
      sub: "extraction · card summary",
    });
    b += node(752, 342, 224, 58, {
      icon: "link",
      title: "Embedding model",
      sub: "in-database ONNX",
    });
    b += arrow(
      [
        [694, 291],
        [752, 291],
      ],
      { kind: "write", label: "extract", at: [723, 283] }
    );
    b += arrow(
      [
        [694, 371],
        [752, 371],
      ],
      { kind: "read", label: "embed", at: [723, 363] }
    );
    b += text(752, 436, "One local model plays both", { cls: "note" });
    b += text(752, 454, "LLM roles here.", { cls: "note" });
    b += text(752, 486, "Scope is enforced in SQL", { cls: "note" });
    b += text(752, 504, "before anything is ranked.", { cls: "note" });
    // data
    b += box(26, 500, 668, 124, {
      title: "Oracle AI Database · one converged engine",
      ic: "db",
      kind: "data",
    });
    b += text(44, 556, "CITY_", { cls: "mono-lbl" });
    b += pills(92, 538, [
      ["ASSET", "data"],
      ["INSPECTION_FINDING", "data"],
      ["THREAD", "memory"],
      ["MESSAGE", "memory"],
      ["MEMORY", "memory"],
    ]);
    b += pills(44, 580, [
      "VECTOR(384)",
      "HNSW index",
      "JSON",
      "SQL scope predicates",
      "in-DB ONNX",
    ]);
    b += arrow(
      [
        [330, 416],
        [330, 500],
      ],
      { kind: "write", label: "write", at: [336, 462], anchor: "start" }
    );
    b += arrow(
      [
        [450, 416],
        [450, 500],
      ],
      { kind: "read", label: "search", at: [456, 462], anchor: "start" }
    );
    b += arrow(
      [
        [560, 500],
        [560, 416],
      ],
      { kind: "read", label: "candidates", at: [566, 462], anchor: "start" }
    );
    return svg(1000, 650, b, {
      title: "CityOps Copilot architecture on Oracle AI Database",
      min: 760,
    });
  };

  /** Overview: the read-then-write loop. */
  F.loop = () => {
    let b = "";
    const xs = [20, 270, 520, 770];
    b +=
      text(20, 26, "READ", { cls: "phase read" }) +
      text(520, 26, "REASON", { cls: "phase model" }) +
      text(770, 26, "WRITE", { cls: "phase write" });
    b += node(xs[0], 38, 200, 80, {
      icon: "db",
      title: "Read the record",
      sub: "asset record",
      sub2: "similar findings",
    });
    b += node(xs[1], 38, 200, 80, {
      icon: "search",
      title: "Recall memory",
      sub: "this thread's card",
      sub2: "asset-pooled records",
    });
    b += node(xs[2], 38, 200, 80, {
      icon: "bulb",
      title: "Ask the LLM",
      sub: "one prompt",
      sub2: "cites the evidence",
    });
    b += node(xs[3], 38, 200, 80, {
      icon: "chat",
      title: "Write the turn",
      sub: "messages stored",
      sub2: "records distilled",
    });
    b += arrow(
      [
        [220, 78],
        [270, 78],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [470, 78],
        [520, 78],
      ],
      { kind: "model" }
    );
    b += arrow(
      [
        [720, 78],
        [770, 78],
      ],
      { kind: "write" }
    );
    b += arrow(
      [
        [870, 118],
        [870, 160],
        [120, 160],
        [120, 118],
      ],
      { kind: "write", dashed: true }
    );
    b += text(495, 184, "the next turn starts better informed — even for a different inspector", {
      cls: "a-lbl write",
      anchor: "middle",
    });
    return svg(1000, 200, b, { title: "Every turn reads, reasons, then writes back" });
  };

  /** Overview: domain data vs memory. */
  F.state = () => {
    let b = "";
    b += layer(10, 30, 400, 250, "Domain data · the system of record", { kind: "data" });
    b += node(26, 70, 368, 62, {
      icon: "bridge",
      title: "CITY_ASSET",
      sub: "Harbor Bridge · bridge  (26 assets)",
    });
    b += node(26, 146, 368, 62, {
      icon: "doc",
      title: "CITY_INSPECTION_FINDING",
      sub: "corrosion · medium · grade C · VECTOR(384)",
    });
    b += pills(26, 232, [["log_finding", "write"]]);
    b += text(140, 251, "deliberate: an inspector decides", { cls: "note" });
    b += layer(590, 30, 400, 250, "Memory · what the agent forms", { kind: "memory" });
    b += node(606, 70, 368, 62, {
      icon: "chat",
      title: "CITY_MESSAGE",
      sub: "verbatim turns, per thread",
    });
    b += node(606, 146, 368, 62, {
      icon: "star",
      title: "CITY_MEMORY",
      sub: "fact · preference · guideline · memory",
    });
    b += pills(606, 232, [["add_messages", "write"]]);
    b += text(726, 251, "automatic: every turn", { cls: "note" });
    b +=
      `<circle cx="500" cy="150" r="40" class="hub"/>` +
      icon("gear", 488, 128, 24) +
      text(500, 172, "copilot", { cls: "n-sub", anchor: "middle" });
    b += arrow(
      [
        [410, 110],
        [462, 136],
      ],
      { kind: "read", label: "reads", at: [430, 104] }
    );
    b += arrow(
      [
        [590, 110],
        [538, 136],
      ],
      { kind: "read", label: "reads", at: [570, 104] }
    );
    b += arrow(
      [
        [538, 166],
        [590, 196],
      ],
      { kind: "write", label: "writes", at: [552, 200], anchor: "end" }
    );
    return svg(1000, 290, b, { title: "Two kinds of state" });
  };

  /** Overview: how the Parts build on each other. */
  F.roadmap = () => {
    let b = "";
    const n = (x, y, w, num, title, sub, href, kind = "") =>
      `<a href="${href}" class="dg-link"><g class="node ${kind}"><rect x="${x}" y="${y}" width="${w}" height="64" rx="10"/>` +
      text(x + 16, y + 39, num, { cls: "num-badge" }) +
      text(x + 46, y + 29, title, { cls: "n-title" }) +
      text(x + 46, y + 47, sub, { cls: "n-sub" }) +
      `</g></a>`;
    b +=
      text(20, 22, "FOUNDATIONS", { cls: "phase muted" }) +
      text(280, 22, "COMPONENTS · build → verify", { cls: "phase read" }) +
      text(580, 22, "ASSEMBLY", { cls: "phase model" }) +
      text(830, 22, "PAYOFF", { cls: "phase write" });
    b += n(20, 64, 190, "1", "Oracle setup", "one converged database", "#/part1");
    b += n(20, 174, 190, "2", "Embedder + SDK", "vectors in the database", "#/part2");
    b += n(280, 34, 230, "3", "Memory + extraction", "report_event()", "#/part3");
    b += n(280, 124, 230, "4", "Findings + vectors", "vector search in SQL", "#/part4");
    b += n(280, 214, 230, "5", "Scoping", "user · agent · thread", "#/part5");
    b += n(580, 124, 190, "6", "call_copilot", "assembles Parts 3–5", "#/part6", "accent");
    b += n(830, 124, 150, "★", "The handoff", "Mercer → Vance", "#/handoff");
    b +=
      arrow(
        [
          [210, 96],
          [245, 96],
        ],
        { end: false }
      ) +
      arrow(
        [
          [210, 206],
          [245, 206],
        ],
        { end: false }
      ) +
      arrow(
        [
          [245, 66],
          [245, 246],
        ],
        { end: false }
      );
    b +=
      arrow([
        [245, 66],
        [280, 66],
      ]) +
      arrow([
        [245, 156],
        [280, 156],
      ]) +
      arrow([
        [245, 246],
        [280, 246],
      ]);
    b +=
      arrow(
        [
          [510, 66],
          [545, 66],
        ],
        { kind: "read", end: false }
      ) +
      arrow(
        [
          [510, 156],
          [545, 156],
        ],
        { kind: "read", end: false }
      ) +
      arrow(
        [
          [510, 246],
          [545, 246],
        ],
        { kind: "read", end: false }
      );
    b +=
      arrow(
        [
          [545, 66],
          [545, 246],
        ],
        { kind: "read", end: false }
      ) +
      arrow(
        [
          [545, 156],
          [580, 156],
        ],
        { kind: "read" }
      );
    b += arrow(
      [
        [770, 156],
        [830, 156],
      ],
      { kind: "model" }
    );
    return svg(1000, 290, b, { title: "How the notebook builds the copilot" });
  };

  /** Part 1: split stack vs converged. */
  F.converged = () => {
    let b = "";
    b += layer(10, 30, 430, 200, "Split stack", { kind: "muted" });
    b += node(28, 70, 180, 60, { icon: "dots", title: "Vector store", sub: "similarity" });
    b += node(242, 70, 180, 60, { icon: "db", title: "Relational DB", sub: "who · what · when" });
    b += arrow(
      [
        [208, 100],
        [242, 100],
      ],
      { kind: "muted", start: true, dashed: true, label: "sync", at: [225, 92] }
    );
    b +=
      icon("cross", 28, 158, 18, "err") +
      text(54, 172, "two copies of the data to keep in step", { cls: "note" });
    b +=
      icon("cross", 28, 186, 18, "err") +
      text(54, 200, "access rules applied after ranking", { cls: "note" });
    b += arrow(
      [
        [448, 130],
        [482, 130],
      ],
      { kind: "data", width: 3 }
    );
    b += layer(490, 30, 500, 214, "Converged · Oracle AI Database", { kind: "data" });
    b += pills(508, 64, [
      ["tables", ""],
      ["JSON", ""],
      ["VECTOR(384)", "data"],
      ["HNSW", "data"],
      ["text", ""],
    ]);
    b += `<rect x="508" y="104" width="464" height="126" rx="10" class="codebox"/>`;
    b += text(524, 130, "SELECT … VECTOR_DISTANCE(embedding, :q, COSINE)", { cls: "code-line" });
    b += text(524, 155, "WHERE asset_id = :asset AND category = :cat", { cls: "code-line" });
    b += text(524, 180, "ORDER BY score FETCH FIRST :k ROWS ONLY", { cls: "code-line" });
    b +=
      icon("check", 524, 196, 16, "ok") +
      text(546, 210, "one statement · one copy · one security model", { cls: "note" });
    return svg(1000, 254, b, { title: "A split stack versus one converged database" });
  };

  /** Part 1: which tables you create and which the SDK creates. */
  F.tables = (prefix = "CITY_") => {
    let b = "";
    b += layer(10, 30, 380, 250, "You create · domain data", { kind: "data" });
    b += node(28, 70, 344, 58, {
      icon: "bridge",
      title: `${prefix}ASSET`,
      sub: "asset_id · asset_class",
    });
    b += node(28, 196, 344, 58, {
      icon: "doc",
      title: `${prefix}INSPECTION_FINDING`,
      sub: "description · recommendation · VECTOR(384)",
    });
    b += arrow(
      [
        [200, 196],
        [200, 128],
      ],
      { kind: "muted", label: "foreign key", at: [206, 166], anchor: "start" }
    );
    b += layer(410, 30, 580, 250, "The SDK creates · memory", { kind: "memory" });
    b += node(428, 70, 262, 58, {
      icon: "layers",
      title: `${prefix}THREAD`,
      sub: "scope · settings · summary",
    });
    b += node(710, 70, 262, 58, {
      icon: "dots",
      title: `${prefix}RECORD_CHUNKS`,
      sub: "vectors + HNSW for search",
    });
    b += node(428, 196, 262, 58, {
      icon: "chat",
      title: `${prefix}MESSAGE`,
      sub: "verbatim, ordered",
    });
    b += node(710, 196, 262, 58, {
      icon: "star",
      title: `${prefix}MEMORY`,
      sub: "typed records + metadata",
    });
    b += arrow(
      [
        [559, 196],
        [559, 128],
      ],
      { kind: "muted", label: "thread_id", at: [565, 166], anchor: "start" }
    );
    b += arrow(
      [
        [730, 196],
        [672, 128],
      ],
      { kind: "muted" }
    );
    b += arrow(
      [
        [841, 196],
        [841, 128],
      ],
      { kind: "read", dashed: true, label: "embedded", at: [847, 166], anchor: "start" }
    );
    return svg(1000, 290, b, { title: "Tables you create and tables the SDK creates" });
  };

  /** Part 2: text to vector to distance. */
  F.embedPipeline = (model = "ALL_MINILM_L12_V2") => {
    let b = "";
    b += node(10, 60, 200, 64, { icon: "doc", title: "Text", sub: "a narrative or a query" });
    b += layer(250, 22, 330, 158, "Oracle AI Database", { kind: "data" });
    b += node(270, 60, 290, 64, {
      icon: "bolt",
      title: "VECTOR_EMBEDDING()",
      sub: `ONNX ${model}`,
      kind: "data",
    });
    b += text(415, 160, "no API key · no text leaves the database", {
      cls: "note",
      anchor: "middle",
    });
    b += node(620, 60, 160, 64, { icon: "dots", title: "384 numbers", sub: "[0.02, -0.04, …]" });
    b += node(820, 40, 170, 104, {
      title: "Cosine distance",
      sub: "0 · same meaning",
      sub2: "≈1 · unrelated",
    });
    b += arrow(
      [
        [210, 92],
        [270, 92],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [560, 92],
        [620, 92],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [780, 92],
        [820, 92],
      ],
      { kind: "read" }
    );
    return svg(1000, 190, b, { title: "From text to vector to distance" });
  };

  /** Part 2: what OracleAgentMemory is wired to. */
  F.sdkWiring = (llm = "llama3.2", prefix = "CITY_") => {
    let b = "";
    b +=
      text(20, 16, "YOU PROVIDE", { cls: "phase req" }) +
      text(720, 16, "IT DOES", { cls: "phase write" });
    b += node(20, 26, 260, 58, { icon: "db", title: "connection", sub: "Oracle · prism" });
    b += node(20, 116, 260, 58, { icon: "link", title: "embedder", sub: "OracleONNXEmbedder" });
    b += node(20, 206, 260, 58, { icon: "bolt", title: "llm", sub: `Llm("openai/${llm}")` });
    b += node(380, 105, 240, 80, {
      icon: "layers",
      title: "OracleAgentMemory",
      sub: "the memory client",
      kind: "accent",
    });
    b += node(720, 26, 260, 58, {
      icon: "db",
      title: "creates its tables",
      sub: `${prefix}THREAD, MESSAGE, MEMORY…`,
    });
    b += node(720, 116, 260, 58, {
      icon: "sparkle",
      title: "extract_memories",
      sub: "records on every add_messages",
    });
    b += node(720, 206, 260, 58, {
      icon: "check",
      title: "CREATE_IF_NECESSARY",
      sub: "first run creates, then reuses",
    });
    b += arrow(
      [
        [280, 55],
        [330, 55],
        [330, 125],
        [380, 125],
      ],
      { kind: "req" }
    );
    b += arrow(
      [
        [280, 145],
        [380, 145],
      ],
      { kind: "req" }
    );
    b += arrow(
      [
        [280, 235],
        [330, 235],
        [330, 165],
        [380, 165],
      ],
      { kind: "req" }
    );
    b += arrow(
      [
        [620, 125],
        [670, 125],
        [670, 55],
        [720, 55],
      ],
      { kind: "write" }
    );
    b += arrow(
      [
        [620, 145],
        [720, 145],
      ],
      { kind: "write" }
    );
    b += arrow(
      [
        [620, 165],
        [670, 165],
        [670, 235],
        [720, 235],
      ],
      { kind: "write" }
    );
    return svg(1000, 272, b, { title: "What the memory client is wired to" });
  };

  /** Part 3: one add_messages call, two kinds of memory. */
  F.addMessages = (prefix = "CITY_") => {
    let b = "";
    b += node(10, 120, 220, 80, {
      icon: "chat",
      title: "Narrative",
      sub: "[Asset: …] [Inspector: …]",
      sub2: "rust bleed near Pier 2…",
    });
    b += node(280, 130, 170, 60, {
      icon: "gear",
      title: "add_messages()",
      sub: "one call",
      kind: "accent",
    });
    b += arrow(
      [
        [230, 160],
        [280, 160],
      ],
      { kind: "req" }
    );
    b += node(540, 30, 220, 64, {
      icon: "chat",
      title: `${prefix}MESSAGE`,
      sub: "verbatim · in order",
    });
    b +=
      text(778, 56, "EPISODIC", { cls: "phase muted" }) +
      text(778, 76, "what was said · thread-local", { cls: "note" });
    b += arrow(
      [
        [450, 150],
        [495, 150],
        [495, 62],
        [540, 62],
      ],
      { kind: "write", label: "store", at: [501, 112], anchor: "start" }
    );
    b += node(540, 196, 220, 64, {
      icon: "sparkle",
      title: "Extractor LLM",
      sub: "the SDK writes its prompt",
      kind: "model",
    });
    b += arrow(
      [
        [450, 170],
        [495, 170],
        [495, 228],
        [540, 228],
      ],
      { kind: "write", label: "distil", at: [501, 210], anchor: "start" }
    );
    b += text(540, 284, "it reads the new messages, the", { cls: "note" });
    b += text(540, 301, "running summary and past memories", { cls: "note" });
    b += node(800, 196, 190, 64, {
      icon: "star",
      title: `${prefix}MEMORY`,
      sub: "typed, reusable",
    });
    b += arrow(
      [
        [760, 228],
        [800, 228],
      ],
      { kind: "write" }
    );
    b += pills(
      800,
      272,
      [
        ["fact", "t-fact"],
        ["guideline", "t-guideline"],
      ],
      { size: 11, h: 24 }
    );
    b += pills(
      800,
      302,
      [
        ["preference", "t-preference"],
        ["memory", "t-memory"],
      ],
      { size: 11, h: 24 }
    );
    return svg(1000, 336, b, { title: "One add_messages call writes two kinds of memory" });
  };

  /** Part 3: scope-matched search. */
  F.scopeSearch = () => {
    let b = "";
    b += layer(10, 22, 340, 176, "thread inspect_demo", { kind: "memory" });
    b += text(26, 62, 'user_id = "inspector_demo"', { cls: "mono-lbl" });
    b += pills(
      26,
      78,
      [
        ["fact", "t-fact"],
        ["guideline", "t-guideline"],
        ["preference", "t-preference"],
      ],
      { size: 11, h: 24 }
    );
    b += text(26, 130, "every record the extractor writes", { cls: "note" });
    b += text(26, 148, "inherits the thread's user_id", { cls: "note" });
    b += node(560, 26, 430, 64, {
      icon: "search",
      title: 'search(user_id="inspector_demo")',
      sub: "same scope → finds the records",
      kind: "okk",
    });
    b += node(560, 122, 430, 64, {
      icon: "search",
      title: "search(user_id=None)",
      sub: "only records with no user → finds nothing",
      kind: "errk",
    });
    b += arrow(
      [
        [350, 70],
        [560, 58],
      ],
      { kind: "ok", label: "match", at: [455, 56] }
    );
    b += arrow(
      [
        [350, 150],
        [560, 154],
      ],
      { kind: "err", dashed: true, label: "no match", at: [455, 144] }
    );
    return svg(1000, 210, b, { title: "Searches match scope exactly" });
  };

  /** Part 4: one SQL statement, three stages. */
  F.hybrid = () => {
    let b = "";
    b += node(10, 80, 180, 64, { icon: "chat", title: "Narrative", sub: "bearing corrosion…" });
    b += node(226, 80, 168, 64, { icon: "bolt", title: "Embed", sub: ":q · VECTOR(384)" });
    b += arrow(
      [
        [190, 112],
        [226, 112],
      ],
      { kind: "read" }
    );
    b += layer(430, 22, 560, 196, "One SQL statement", { kind: "data" });
    b += node(448, 58, 160, 64, { icon: "filter", title: "Filter", sub: "asset · category" });
    b += node(626, 58, 176, 64, { icon: "dots", title: "Rank", sub: "VECTOR_DISTANCE" });
    b += node(820, 58, 152, 64, { icon: "check", title: "Top k", sub: "FETCH FIRST :k" });
    b += arrow(
      [
        [394, 112],
        [418, 112],
        [418, 90],
        [448, 90],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [608, 90],
        [626, 90],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [802, 90],
        [820, 90],
      ],
      { kind: "read" }
    );
    b += text(
      448,
      152,
      "(:asset_id IS NULL OR asset_id = :asset_id) — pass None to switch a filter off",
      { cls: "note" }
    );
    b += text(448, 176, "the HNSW index compares the query with a small fraction of the rows", {
      cls: "note",
    });
    b += text(448, 200, "→ the 3 closest findings on this asset go into the copilot's prompt", {
      cls: "note",
    });
    return svg(1000, 228, b, { title: "Similarity and filters in one SQL statement" });
  };

  /** Part 4: an HNSW search, drawn from seeded points. */
  F.hnsw = () => {
    let seed = 7;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const bands = [
      { y: 60, label: "layer 2 · few nodes, long links" },
      { y: 140, label: "layer 1" },
      { y: 220, label: "layer 0 · every vector" },
    ];
    const pts = Array.from({ length: 22 }, (_, i) => ({
      id: i,
      x: 210 + rnd() * 700,
      dy: (rnd() - 0.5) * 34,
    }));
    const L1 = pts.filter((_, i) => i % 3 === 0),
      L2 = L1.filter((_, i) => i % 2 === 0);
    const layers = [L2, L1, pts];
    const target = { x: 760, dy: 8 };
    const dist = (a, b) => Math.hypot(a.x - b.x, (a.dy - b.dy) * 3);
    const nbrs = (p, set, k = 3) =>
      set
        .filter((q) => q !== p)
        .sort((a, c) => dist(p, a) - dist(p, c))
        .slice(0, k);
    let b = "";
    bands.forEach((band, i) => {
      b +=
        `<rect x="180" y="${band.y - 30}" width="760" height="60" rx="30" class="band"/>` +
        text(14, band.y + 4, band.label, { cls: "note" });
      const set = layers[i];
      const seen = new Set();
      set.forEach((p) =>
        nbrs(p, set).forEach((q) => {
          const key = [p.id, q.id].sort().join("-");
          if (seen.has(key)) return;
          seen.add(key);
          b += `<line x1="${p.x}" y1="${band.y + p.dy}" x2="${q.x}" y2="${band.y + q.dy}" class="edge"/>`;
        })
      );
    });
    // greedy search from the first top-layer node
    let cur = L2[0];
    const path = [];
    layers.forEach((set, i) => {
      if (!set.includes(cur)) cur = set.reduce((a, c) => (dist(c, cur) < dist(a, cur) ? c : a));
      path.push({ p: cur, y: bands[i].y });
      for (let step = 0; step < 6; step++) {
        const better = nbrs(cur, set, 4)
          .filter((q) => dist(q, target) < dist(cur, target))
          .sort((a, c) => dist(a, target) - dist(c, target))[0];
        if (!better) break;
        cur = better;
        path.push({ p: cur, y: bands[i].y });
      }
    });
    for (let i = 1; i < path.length; i++) {
      const a = path[i - 1],
        c = path[i];
      b += `<line x1="${a.p.x}" y1="${a.y + a.p.dy}" x2="${c.p.x}" y2="${c.y + c.p.dy}" class="hop ${a.y !== c.y ? "drop" : ""}"/>`;
    }
    layers.forEach((set, i) =>
      set.forEach((p) => {
        const on = path.some((s) => s.p === p && s.y === bands[i].y);
        b += `<circle cx="${p.x}" cy="${bands[i].y + p.dy}" r="${on ? 5.5 : 4}" class="pt ${on ? "on" : ""}"/>`;
      })
    );
    b +=
      icon("star", target.x - 10, bands[2].y + target.dy - 10, 20, "target") +
      text(target.x + 16, bands[2].y + target.dy + 22, "query", { cls: "a-lbl read" });
    b += text(path[0].p.x, bands[0].y + path[0].p.dy - 14, "entry", {
      cls: "a-lbl read",
      anchor: "middle",
    });
    return svg(1000, 262, b, { title: "How an HNSW index finds nearest neighbours" });
  };

  /** Part 5: who can see what. */
  F.scopeMap = () => {
    let b = "";
    b += layer(10, 22, 980, 384, "agent_id = CITY · the CityOps application", { kind: "sdk" });
    b += layer(28, 58, 584, 330, "user_id = Harbor Bridge · the asset is the principal", {
      kind: "memory",
    });
    const thread = (x, who, avatar) =>
      `<rect x="${x}" y="94" width="270" height="128" rx="10" class="box"/>` +
      icon("lock", x + 12, 104, 16, "muted") +
      text(x + 34, 118, `thread …::${who}`, { cls: "mono-lbl" }) +
      pills(
        x + 14,
        132,
        [
          ["narrative", "t-message"],
          ["answer", "t-message"],
          ["…", "t-message"],
        ],
        { size: 11, h: 24 }
      ) +
      text(x + 14, 182, "raw messages: only this", { cls: "note" }) +
      text(x + 14, 199, `inspector's context card sees them`, { cls: "note" }) +
      `<circle cx="${x + 252}" cy="112" r="11" class="avatar-dot ${avatar}"/>`;
    b += thread(44, "Evelyn_H_Mercer", "mercer") + thread(328, "Jordan_Vance", "vance");
    b += arrow(
      [
        [179, 222],
        [179, 262],
      ],
      { kind: "write", dashed: true, label: "extractor", at: [185, 248], anchor: "start" }
    );
    b += arrow(
      [
        [463, 222],
        [463, 262],
      ],
      { kind: "write", dashed: true, label: "extractor", at: [469, 248], anchor: "start" }
    );
    b += `<rect x="44" y="262" width="554" height="110" rx="10" class="box pooled"/>`;
    b += text(60, 286, "RECORDS POOLED UNDER THE ASSET", { cls: "path-lbl read" });
    b += pills(
      60,
      298,
      [
        ["fact", "t-fact"],
        ["guideline", "t-guideline"],
        ["guideline", "t-guideline"],
        ["fact", "t-fact"],
        ["memory", "t-memory"],
      ],
      { size: 11, h: 24 }
    );
    b +=
      icon("search", 60, 334, 16, "read") +
      text(
        82,
        348,
        "seen by any copilot turn on Harbor Bridge (step 4b) — never the raw messages",
        { cls: "note" }
      );
    b += layer(632, 58, 340, 144, "user_id = Evelyn_H_Mercer", { kind: "muted" });
    b +=
      pills(648, 94, [["memory", "t-memory"]], { size: 11, h: 24 }) +
      text(726, 111, "swap shifts with Jordan…", { cls: "note" });
    b +=
      icon("lock", 648, 140, 16, "muted") +
      text(670, 154, "only Mercer's own searches", { cls: "note" }) +
      text(670, 172, "match this personal note", { cls: "note" });
    b += layer(632, 218, 340, 170, "no user_id · city-wide", { kind: "muted" });
    b +=
      pills(648, 254, [["memory", "t-memory"]], { size: 11, h: 24 }) +
      text(726, 271, "inspect Pier 2 annually…", { cls: "note" });
    b +=
      icon("search", 648, 300, 16, "read") +
      text(670, 314, "any inspector's city-scope", { cls: "note" }) +
      text(670, 332, "search (user_id=None,", { cls: "note" }) +
      text(670, 350, 'agent_id="CITY") finds it', { cls: "note" });
    return svg(1000, 416, b, { title: "Who can see which memories", min: 760 });
  };

  /** Part 6: the eight steps; live jobs light the nodes up. */
  const TURN = [
    ["thread", 20, 40, "chat", "1 · Thread", "asset::inspector", "sdk"],
    ["asset", 210, 40, "bridge", "2 · Asset", "CITY_ASSET", "data"],
    ["card", 400, 40, "book", "3 · Context card", "this thread only", "memory"],
    ["similar", 590, 40, "search", "4 · Findings", "vector SQL, k = 3", "data"],
    ["pooled", 780, 40, "layers", "4b · Pooled", "the asset's records", "memory"],
    ["prompt", 110, 200, "doc", "5 · Prompt", "five sections", ""],
    ["answer", 360, 200, "bulb", "6 · Agent LLM", "the diagnosis", "model"],
    ["persist", 600, 200, "chat", "7 · add_messages", "store + extract", "write"],
    ["learned", 800, 200, "sparkle", "8 · Learned", "the new records", "write"],
  ];
  F.turnMap = () => {
    let b = "";
    b +=
      text(20, 26, "READ · steps 1–4b", { cls: "phase read" }) +
      text(110, 190, "REASON", { cls: "phase model" }) +
      text(600, 190, "WRITE", { cls: "phase write" });
    for (const [key, x, y, ic, title, sub, kind] of TURN) {
      const w = key === "prompt" || key === "answer" ? 190 : 180;
      b += node(x, y, key === "persist" ? 184 : w, 74, {
        icon: ic,
        title,
        sub,
        kind: `step ${kind}`,
        id: `tm-${key}`,
        tsize: 14.5,
      });
      b += text(x + (key === "persist" ? 184 : w) - 10, y + 16, "", {
        cls: "tm-ms",
        anchor: "end",
      }).replace("<text", `<text id="tm-ms-${key}"`);
    }
    for (const xc of [110, 300, 490, 680, 870])
      b += arrow(
        [
          [xc, 114],
          [xc, 150],
        ],
        { kind: "read", end: false }
      );
    b += arrow(
      [
        [110, 150],
        [870, 150],
      ],
      { kind: "read", end: false }
    );
    b += arrow(
      [
        [205, 150],
        [205, 200],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [300, 237],
        [360, 237],
      ],
      { kind: "model" }
    );
    b += arrow(
      [
        [550, 237],
        [600, 237],
      ],
      { kind: "write" }
    );
    b += arrow(
      [
        [784, 237],
        [800, 237],
      ],
      { kind: "write" }
    );
    b += arrow(
      [
        [980, 237],
        [992, 237],
        [992, 14],
        [870, 14],
        [870, 40],
      ],
      { kind: "write", dashed: true }
    );
    b += arrow(
      [
        [870, 14],
        [490, 14],
        [490, 40],
      ],
      { kind: "write", dashed: true }
    );
    b += text(700, 9, "what this turn writes, the next turn reads", {
      cls: "a-lbl write",
      anchor: "middle",
    });
    b += text(
      500,
      300,
      "three model calls per turn: the card summary (step 3) and extraction (inside step 7) use the SDK's LLM; step 6 is the agent's",
      { cls: "note", anchor: "middle" }
    );
    return svg(1000, 312, b, {
      title: "The eight steps of one copilot turn",
      cls: "turnmap",
      min: 760,
    });
  };
  /** Light up the turn map from a job's step statuses. */
  F.turnMapUpdate = (root, job) => {
    if (!root || !job) return;
    for (const s of job.steps) {
      const g = root.querySelector(`#tm-${s.key}`);
      if (!g) continue;
      g.classList.remove("pending", "running", "done", "error");
      g.classList.add(s.status);
      const ms = root.querySelector(`#tm-ms-${s.key}`);
      if (ms) ms.textContent = s.ms != null ? App.fmtMs(s.ms) : s.status === "running" ? "…" : "";
    }
  };

  /** Handoff: the two routes from Mercer to Vance. */
  F.handoff = () => {
    let b = "";
    b += layer(10, 22, 300, 330, "Day 1 · Mercer writes");
    b +=
      `<circle cx="44" cy="80" r="15" class="avatar-dot mercer"/>` +
      text(70, 76, "Evelyn H. Mercer", { cls: "n-title" }) +
      text(70, 94, "Harbor Bridge, Pier 2", { cls: "n-sub" });
    b += node(26, 132, 268, 70, {
      icon: "chat",
      title: "call_copilot ×2",
      sub: "her private thread",
      sub2: "…::Evelyn_H_Mercer",
    });
    b += node(26, 250, 268, 70, {
      icon: "doc",
      title: "log_finding",
      sub: "corrosion · grade C",
      sub2: "primer within 60 days",
    });
    b += layer(350, 22, 300, 330, "Oracle · shared by asset", { kind: "data" });
    b += node(366, 132, 268, 70, {
      icon: "star",
      title: "Pooled records",
      sub: "user_id = Harbor Bridge",
      sub2: "facts + guidelines",
      id: "hf-pooled",
    });
    b += node(366, 250, 268, 70, {
      icon: "db",
      title: "INSPECTION_FINDING",
      sub: "her finding, embedded",
      sub2: "VECTOR(384)",
      id: "hf-finding",
    });
    b += arrow(
      [
        [294, 167],
        [366, 167],
      ],
      { kind: "write", label: "extractor", at: [330, 159] }
    );
    b += arrow(
      [
        [294, 285],
        [366, 285],
      ],
      { kind: "write", label: "INSERT", at: [330, 277] }
    );
    b += layer(690, 22, 300, 330, "Day N · Vance reads");
    b +=
      `<circle cx="724" cy="80" r="15" class="avatar-dot vance"/>` +
      text(750, 76, "Jordan Vance", { cls: "n-title" }) +
      text(750, 94, "never met Mercer", { cls: "n-sub" });
    b += node(706, 132, 268, 70, {
      icon: "layers",
      title: "step 4b · pooled search",
      sub: "her lessons arrive",
      sub2: "",
      id: "hf-4b",
    });
    b += node(706, 250, 268, 70, {
      icon: "search",
      title: "step 4 · similar findings",
      sub: "her finding arrives",
      sub2: "",
      id: "hf-4",
    });
    b += arrow(
      [
        [634, 167],
        [706, 167],
      ],
      { kind: "read", label: "records", at: [670, 159] }
    );
    b += arrow(
      [
        [634, 285],
        [706, 285],
      ],
      { kind: "read", label: "vectors", at: [670, 277] }
    );
    b +=
      icon("lock", 26, 222, 15, "muted") +
      text(46, 234, "her raw messages never leave her thread", { cls: "note" });
    b += text(
      500,
      374,
      "Two routes, no human handoff: structured evidence by vector search, operating knowledge by pooled memory.",
      { cls: "note", anchor: "middle" }
    );
    return svg(1000, 384, b, {
      title: "How Mercer's work reaches Vance",
      cls: "handoff-fig",
      min: 760,
    });
  };
  F.handoffUpdate = (root, vance) => {
    if (!root || !vance) return;
    const fromMercer = (vance.pooled || []).filter((r) =>
      (r.thread_id || "").endsWith("::Evelyn_H_Mercer")
    ).length;
    const rank = (vance.similar || []).findIndex((r) => r.inspector === "Evelyn_H_Mercer");
    const set = (id, line, ok) => {
      const g = root.querySelector(id);
      if (!g) return;
      const t = g.querySelector("text.n-sub");
      if (t) t.textContent = line;
      g.classList.toggle("done", ok);
    };
    set(
      "#hf-4b",
      `${fromMercer} of ${(vance.pooled || []).length} records from Mercer`,
      fromMercer > 0
    );
    set(
      "#hf-4",
      rank >= 0 ? `her finding ranked #${rank + 1} of 3` : "not in the top 3 this time",
      rank >= 0
    );
  };

  /** Wrap-up: cognitive memory types to what implements them here. */
  F.memoryMap = () => {
    const rows = [
      ["Working memory", "the prompt + the context card", "", "book"],
      ["Episodic · conversations", "CITY_MESSAGE, per thread", "message", "chat"],
      ["Episodic · summaries", "the rolling thread summary", "", "layers"],
      ["Semantic · knowledge", "facts + vector-searched findings", "fact", "db"],
      ["Procedural · rules", "guideline records", "guideline", "check"],
      ["Persona · preferences", "preference records", "preference", "users"],
      ["Shared · coordination", "asset-pooled + agent-scoped memory", "memory", "link"],
    ];
    let b =
      text(20, 20, "COGNITIVE MEMORY TYPE", { cls: "phase muted" }) +
      text(380, 20, "SDK RECORD TYPE", { cls: "phase read" }) +
      text(600, 20, "WHAT IMPLEMENTS IT HERE", { cls: "phase write" });
    rows.forEach(([type, impl, chip, ic], i) => {
      const y = 32 + i * 52;
      b += node(20, y, 300, 42, { icon: ic, title: type });
      b += node(600, y, 380, 42, { title: impl, kind: "impl" });
      b += arrow(
        [
          [320, y + 21],
          [600, y + 21],
        ],
        { kind: "muted", end: true }
      );
      if (chip) {
        const p = pill(460 - (tw(chip, 11) + 24) / 2, y + 9, chip, {
          kind: `t-${chip}`,
          size: 11,
          h: 24,
        });
        b += p.svg;
      }
    });
    const y = 32 + rows.length * 52 + 6;
    b +=
      `<rect x="20" y="${y}" width="960" height="40" rx="10" class="layer muted"/>` +
      text(
        36,
        y + 25,
        "Left to the agent framework, not the memory layer: semantic cache · toolbox · workflows · tool logs",
        { cls: "note" }
      );
    return svg(1000, y + 50, b, { title: "Memory types mapped to what implements them" });
  };

  /** Part 2 (live): place sentences in 2-D from their cosine distances (classical MDS). */
  F.meaningMap = (labels, texts, D2) => {
    const n = labels.length;
    const sq = D2.map((r) => r.map((d) => d * d));
    const rowMean = sq.map((r) => r.reduce((a, v) => a + v, 0) / n);
    const all = rowMean.reduce((a, v) => a + v, 0) / n;
    const B = sq.map((r, i) => r.map((v, j) => -0.5 * (v - rowMean[i] - rowMean[j] + all)));
    const power = (M, deflate) => {
      let v = Array.from({ length: n }, (_, i) => 1 + i * 0.37);
      let lambda = 0;
      for (let it = 0; it < 200; it++) {
        let w = M.map((r) => r.reduce((a, x, j) => a + x * v[j], 0));
        if (deflate) {
          const dot = w.reduce((a, x, i) => a + x * deflate.v[i], 0);
          w = w.map((x, i) => x - dot * deflate.v[i]);
        }
        const norm = Math.hypot(...w) || 1;
        v = w.map((x) => x / norm);
        lambda = norm;
      }
      return { v, lambda };
    };
    const e1 = power(B),
      e2 =
        n > 2
          ? power(
              B.map((r, i) => r.map((x, j) => x - e1.lambda * e1.v[i] * e1.v[j])),
              e1
            )
          : { v: Array(n).fill(0), lambda: 0 };
    const pts = labels.map((_, i) => [
      e1.v[i] * Math.sqrt(Math.max(e1.lambda, 0)),
      e2.v[i] * Math.sqrt(Math.max(e2.lambda, 0)),
    ]);
    const W = 1000,
      H = 300;
    const xs = pts.map((p) => p[0]),
      ys = pts.map((p) => p[1]);
    const span = Math.max(
      Math.max(...xs) - Math.min(...xs),
      Math.max(...ys) - Math.min(...ys),
      1e-6
    );
    const cx = (Math.max(...xs) + Math.min(...xs)) / 2,
      cy = (Math.max(...ys) + Math.min(...ys)) / 2;
    // points stay in the middle 400 px so each sentence has room beside its point
    const sx = (x) => W / 2 + ((x - cx) / span) * 400;
    const sy = (y) => H / 2 + 12 + ((y - cy) / span) * 400 * 0.4;
    let b = "";
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        const close = D2[i][j] < 0.5;
        const x1 = sx(pts[i][0]),
          y1 = sy(pts[i][1]),
          x2 = sx(pts[j][0]),
          y2 = sy(pts[j][1]);
        b += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="mm-edge ${close ? "close" : ""}"/>`;
        // label beside the line (perpendicular offset), so it never sits under a point
        const len = Math.hypot(x2 - x1, y2 - y1) || 1,
          ox = (-(y2 - y1) / len) * 18,
          oy = ((x2 - x1) / len) * 18;
        b += text((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy + 4, D2[i][j].toFixed(3), {
          cls: `a-lbl ${close ? "read" : "muted"}`,
          anchor: "middle",
        });
      }
    pts.forEach((p, i) => {
      const x = sx(p[0]),
        y = sy(p[1]),
        right = x < W / 2;
      b +=
        `<circle cx="${x}" cy="${y}" r="20" class="mm-pt"/>` +
        text(x, y + 6, labels[i], { cls: "mm-lbl", anchor: "middle" });
      // the sentence sits beside its point, on the side facing the middle of the map
      b += text(right ? x - 28 : x + 28, y + 5, App.trunc(texts[i], 34), {
        cls: "a-lbl muted",
        anchor: right ? "end" : "start",
      });
    });
    b += text(16, 22, "MEANING MAP · positions from the cosine distances, flattened to 2-D", {
      cls: "phase muted",
    });
    return svg(W, H, b, { title: "Sentences placed by meaning" });
  };

  return { F, svg, node, arrow, layer, pills, pill, text, icon };
})();
