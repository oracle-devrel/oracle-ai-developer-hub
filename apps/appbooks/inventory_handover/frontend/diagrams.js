/* The inventory notebook's diagrams, drawn with the toolkit in figures.js.
   Arrow colours: amber = request/answer, salmon = write path, blue = read path,
   violet = model call, gold = data. Figures that take results redraw from live runs. */

(() => {
  const { F, svg, node, arrow, layer, pills, pill, text, icon, box, tw } = D;
  const esc = App.esc;
  const wrap = (s, n) => {
    const out = [];
    String(s || "")
      .replace(/\*\*/g, "")
      .split(/\n|;\s*/)
      .map((l) => l.trim())
      .filter(Boolean)
      .forEach((line) => {
        let cur = "";
        line.split(" ").forEach((w) => {
          if ((cur + " " + w).trim().length > n) {
            out.push(cur.trim());
            cur = w;
          } else cur += " " + w;
        });
        if (cur.trim()) out.push(cur.trim());
      });
    return out;
  };

  /* -------------------------------------------------- overview */

  F.story = () => {
    let b = text(10, 24, "RESTOCK-101 · CERAMIC MUG SKU-MUG-01 · EVERYDAY GOODS", {
      cls: "phase muted",
    });
    const S = [
      [
        10,
        "user",
        "1 · Request",
        "Alice proposes 80 mugs",
        "request PO-1048",
        "proposal — awaiting approval",
        "req",
      ],
      [
        260,
        "check",
        "2 · Decision",
        "Manager approves 120",
        "same request, replaces 80",
        "replaces 80 — don't add them",
        "data",
      ],
      [
        510,
        "clock",
        "3 · Still pending",
        "No supplier order yet",
        "delivery unconfirmed",
        "approval is not an order",
        "write",
      ],
      [
        760,
        "refresh",
        "4 · Handover",
        "A new planner, a new chat",
        "needs the latest decision",
        "without Alice's chat open",
        "read",
      ],
    ];
    S.forEach(([x, ic, title, sub, sub2, tag, kind], i) => {
      b += node(x, 44, 230, 92, { icon: ic, title, sub, sub2 });
      b += pills(x, 146, [[tag, kind]], { size: 11, h: 24 });
      if (i < 3)
        b += arrow(
          [
            [x + 230, 90],
            [x + 250, 90],
          ],
          { kind: "req" }
        );
    });
    b +=
      icon("cross", 10, 196, 16, "err") +
      text(
        32,
        209,
        "Bob's RET-771 tote-bag returns is a different product and workflow — it must stay out of the mug handover.",
        { cls: "note" }
      );
    return svg(1000, 226, b, { title: "The mug replenishment story" });
  };

  F.architecture = (store = "ZH_INVENTORY") => {
    let b = "";
    b += layer(10, 34, 700, 112, "Application layer");
    b += layer(10, 196, 186, 236, "Host controls");
    b += layer(206, 196, 504, 236, "Memory layer");
    b += layer(10, 470, 700, 176, "Data layer", { kind: "data" });
    b += layer(730, 34, 260, 612, "Model layer");
    b += node(26, 66, 160, 58, { icon: "users", title: "Planner", sub: "asks the question" });
    b += node(262, 66, 190, 58, { icon: "gear", title: "Agent loop", sub: "create_agent + tools" });
    b += node(510, 66, 170, 58, {
      icon: "book",
      title: "Context window",
      sub: "working memory",
      tsize: 14,
    });
    b += arrow(
      [
        [186, 95],
        [262, 95],
      ],
      { kind: "req", label: "question", at: [224, 87] }
    );
    b += arrow(
      [
        [452, 95],
        [510, 95],
      ],
      { kind: "req", label: "builds", at: [481, 87] }
    );
    b += arrow(
      [
        [680, 95],
        [752, 95],
      ],
      { kind: "req", label: "tokens in", at: [716, 87] }
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
    b += node(24, 226, 158, 64, { icon: "key", title: "Review gate", sub: "exact-draft approval" });
    b += node(24, 314, 158, 64, {
      icon: "filter",
      title: "Tool scopes",
      sub: "host picks evidence",
    });
    b += arrow(
      [
        [70, 124],
        [70, 226],
      ],
      { kind: "write", label: "approves", at: [76, 160], anchor: "start" }
    );
    b += arrow(
      [
        [182, 258],
        [222, 258],
      ],
      { kind: "write" }
    );
    b += arrow(
      [
        [182, 346],
        [222, 346],
      ],
      { kind: "read" }
    );
    b += box(222, 226, 472, 190, {
      title: "Oracle AI Agent Memory · OAMP 26.8",
      ic: "layers",
      kind: "sdk",
    });
    b += text(240, 278, "WRITE PATH · retain, refine", { cls: "path-lbl write" });
    b += pills(240, 288, [
      ["add_messages", "write"],
      ["extraction", "write"],
      ["link_records", "write"],
      ["ttl_days", "write"],
    ]);
    b += text(240, 350, "READ PATH · recall, reuse", { cls: "path-lbl read" });
    b += pills(240, 360, [
      ["search + filters", "read"],
      ["num_hops", "read"],
      ["pruning", "read"],
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
      { kind: "read", label: "recall + scope", at: [416, 182], anchor: "start" }
    );
    b += arrow(
      [
        [595, 226],
        [595, 124],
      ],
      { kind: "read", label: "context card", at: [601, 182], anchor: "start" }
    );
    b += node(752, 66, 224, 58, {
      icon: "bulb",
      title: "Grok 4.3 · agent",
      sub: "ChatOpenAI → /openai/v1",
    });
    b += node(752, 262, 224, 72, {
      icon: "bolt",
      title: "OAMP Llm",
      sub: "extraction · pruning",
      sub2: "summaries · links",
    });
    b += node(752, 352, 224, 58, {
      icon: "link",
      title: "Embedding model",
      sub: "in-database ONNX",
    });
    b += arrow(
      [
        [694, 298],
        [752, 298],
      ],
      { kind: "write", label: "LLM", at: [723, 290] }
    );
    b += arrow(
      [
        [694, 381],
        [752, 381],
      ],
      { kind: "read", label: "embed", at: [723, 373] }
    );
    b +=
      text(752, 446, "One Grok model plays both", { cls: "note" }) +
      text(752, 464, "LLM roles, via two APIs.", { cls: "note" });
    b +=
      text(752, 496, "Filters select evidence;", { cls: "note" }) +
      text(752, 514, "they are not permissions.", { cls: "note" });
    b += box(26, 500, 668, 130, { title: "Oracle AI Database · prism", ic: "db", kind: "data" });
    b += text(44, 556, `${store}_`, { cls: "mono-lbl" });
    b += pills(150, 538, [
      ["THREAD", "memory"],
      ["MESSAGE", "memory"],
      ["MEMORY", "memory"],
      ["MEMORY_LINK", "memory"],
      ["RECORD_CHUNKS", "memory"],
    ]);
    b += pills(44, 588, [
      ["VECTOR(384)", "data"],
      ["HNSW", "data"],
      "JSON metadata",
      "SQL filters",
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
    return svg(1000, 656, b, {
      title: "The memory aware inventory agent on Oracle AI Database",
      min: 760,
    });
  };

  F.memoryRoles = () => {
    let b = node(10, 22, 980, 86, {
      icon: "book",
      title: "Working memory — the LLM's context window",
      sub: "What is available for this reasoning step? Instructions, the question, selected messages, retrieved facts and tool results.",
      sub2: "Lifetime: one model call. It carries forward only if the application supplies it again.",
      kind: "accent",
    });
    b += text(10, 180, "DURABLE · ORACLE AGENT MEMORY", { cls: "phase muted" });
    const R = [
      [
        10,
        "chat",
        "Episodic memory",
        "What happened, and in what order?",
        "shift messages · worksheet · summaries",
      ],
      [
        342,
        "star",
        "Semantic memory",
        "What do we currently know?",
        "120 approved · PO-1048 · supersedes 80",
      ],
      [
        674,
        "check",
        "Procedural memory",
        "How to handle the next similar task?",
        "approved SOPs · a reviewed checklist",
      ],
    ];
    R.forEach(([x, ic, title, sub, sub2]) => {
      b += node(x, 192, 316, 84, { icon: ic, title, sub, sub2 });
      b += arrow(
        [
          [x + 158, 192],
          [x + 158, 108],
        ],
        { kind: "read", label: "recall", at: [x + 164, 156], anchor: "start" }
      );
    });
    return svg(1000, 290, b, { title: "Four memory roles" });
  };

  F.engineering = () => {
    let b = layer(10, 20, 470, 270, "Memory engineering · over time", { kind: "memory" });
    b += node(26, 60, 208, 64, { icon: "chat", title: "Retain", sub: "messages → typed records" });
    b += node(256, 60, 208, 64, { icon: "refresh", title: "Reuse", sub: "a new session recalls" });
    b += node(256, 176, 208, 64, {
      icon: "check",
      title: "Refine",
      sub: "supersede, keep history",
    });
    b += node(26, 176, 208, 64, {
      icon: "search",
      title: "Recall",
      sub: "filters + vectors + budget",
    });
    b +=
      arrow(
        [
          [234, 92],
          [256, 92],
        ],
        { kind: "write" }
      ) +
      arrow(
        [
          [360, 124],
          [360, 176],
        ],
        { kind: "write" }
      );
    b +=
      arrow(
        [
          [256, 208],
          [234, 208],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [130, 176],
          [130, 124],
        ],
        { kind: "read" }
      );
    b += text(245, 272, "what becomes durable, how it evolves, how it returns", {
      cls: "note",
      anchor: "middle",
    });
    b += arrow(
      [
        [480, 155],
        [500, 155],
      ],
      { kind: "data", width: 3 }
    );
    b += layer(500, 20, 490, 270, "Context engineering · this turn", { kind: "sdk" });
    const bars = [
      ["all durable records", 440],
      ["select: user · type · source", 380],
      ["rank by similarity", 320],
      ["fit a token budget", 260],
      ["label, then present", 200],
    ];
    bars.forEach(([lbl, w], i) => {
      const y = 50 + i * 40;
      b +=
        `<rect x="${745 - w / 2}" y="${y}" width="${w}" height="30" rx="8" class="box ${i === 4 ? "sdk" : ""}"/>` +
        text(745, y + 20, lbl, { cls: "n-sub", anchor: "middle" });
    });
    b += text(745, 272, "high signal, low noise in the context window", {
      cls: "note",
      anchor: "middle",
    });
    return svg(1000, 300, b, {
      title: "Memory engineering prepares records; context engineering selects them",
    });
  };

  /** The four stages; `rows` are the live comparison rows (Part 7.4). */
  F.journey = (rows = []) => {
    const H = [
      [
        "bulb",
        "Bare LLM",
        "notes in the prompt",
        "Quantity: 120; Approval request: PO-1048 approved; Order status: not submitted",
      ],
      [
        "bulb",
        "Bare LLM",
        "new call, question only",
        "Quantity: unknown; Approval request: unknown; Order status: unknown",
      ],
      [
        "gear",
        "Agent loop",
        "new chat · SOP tool only",
        "Quantity: unknown; Approval request: unknown; Order status: unknown",
      ],
      [
        "layers",
        "Memory aware agent",
        "new chat · Oracle recall",
        "Quantity: 120; Approval request: PO-1048 approved; Order status: not submitted",
      ],
    ];
    let b = "";
    H.forEach(([ic, title, sub, expected], i) => {
      const x = 10 + i * 248;
      const live = rows[i] && rows[i].answer;
      const answer = live || expected;
      const ok = /\b120\b/.test(answer);
      b += node(x, 20, 236, 58, { icon: ic, title, sub, kind: i === 3 ? "accent" : "" });
      if (i < 3)
        b += arrow(
          [
            [x + 236, 49],
            [x + 248, 49],
          ],
          { kind: "muted" }
        );
      b += `<rect x="${x}" y="96" width="236" height="132" rx="10" class="box ${ok ? "pooled" : ""}"/>`;
      b += text(x + 12, 116, live ? "ACTUAL ANSWER" : "NOTEBOOK RUN", { cls: "phase muted" });
      wrap(answer, 30)
        .slice(0, 5)
        .forEach(
          (line, k) => (b += text(x + 12, 140 + k * 17, line, { cls: "code-line", size: 12 }))
        );
      b += pills(x, 240, [[ok ? "has the decision" : "decision unknown", ok ? "read" : "write"]], {
        size: 11,
        h: 24,
      });
    });
    b += text(
      500,
      292,
      "Same model, same question — only the evidence the call can reach changes.",
      { cls: "note", anchor: "middle" }
    );
    return svg(1000, 304, b, { title: "Four stages of the agent", cls: "journey-fig" });
  };

  F.roadmap = () => {
    const P = [
      ["4", "A bare LLM", "context window", "#/part4"],
      ["5", "An agent loop", "tools, no memory", "#/part5"],
      ["6", "Durable memory", "retain + refine", "#/part6"],
      ["7", "Memory aware", "recall in a new chat", "#/part7"],
      ["8", "Working context", "retrieve + curate", "#/part8"],
      ["9", "Review + lifecycle", "approve, reuse, expire", "#/part9"],
    ];
    let b =
      text(10, 22, "WITHOUT MEMORY", { cls: "phase write" }) +
      text(340, 22, "WITH DURABLE MEMORY IN ORACLE", { cls: "phase read" });
    P.forEach(([n, title, sub, href], i) => {
      const x = 10 + i * 166;
      b +=
        `<a href="${href}" class="dg-link"><g class="node ${i === 3 ? "accent" : ""}"><rect x="${x}" y="36" width="154" height="64" rx="10"/>` +
        text(x + 14, 75, n, { cls: "num-badge" }) +
        text(x + 36, 63, title, { cls: "n-title", size: 13.5 }) +
        text(x + 36, 81, sub, { cls: "n-sub", size: 11.5 }) +
        "</g></a>";
      if (i < 5)
        b += arrow(
          [
            [x + 154, 68],
            [x + 166, 68],
          ],
          { kind: i < 1 ? "muted" : "read" }
        );
    });
    return svg(1000, 112, b, { title: "Parts 4–9" });
  };

  /* -------------------------------------------------- Parts 3–5 */

  F.twoClients = (model = "xai.grok-4.3", region = "us-chicago-1") => {
    let b = node(10, 70, 210, 72, {
      icon: "gear",
      title: "LangChain agent",
      sub: "ChatOpenAI",
      sub2: "answers + tool calls",
    });
    b += node(10, 170, 210, 72, {
      icon: "layers",
      title: "OAMP",
      sub: "Llm (LiteLLM route)",
      sub2: "extract · summarise · prune",
    });
    b += layer(300, 40, 420, 230, `OCI Generative AI · ${region}`, { kind: "sdk" });
    b += node(320, 80, 380, 58, {
      icon: "link",
      title: "/openai/v1 · OpenAI-compatible API",
      tsize: 13.5,
      sub: "the agent's client",
    });
    b += node(320, 180, 380, 58, {
      icon: "link",
      title: "the same API (API key) or OCI native chat",
      tsize: 13.5,
      sub: "OAMP's client (config-file signing)",
    });
    b +=
      arrow(
        [
          [220, 106],
          [320, 109],
        ],
        { kind: "req" }
      ) +
      arrow(
        [
          [220, 206],
          [320, 209],
        ],
        { kind: "req" }
      );
    b += node(780, 120, 200, 72, {
      icon: "bulb",
      title: model,
      tsize: 14,
      sub: "a reasoning model",
      sub2: "max 4,096 tokens out",
      kind: "model",
    });
    b +=
      arrow(
        [
          [700, 109],
          [740, 109],
          [740, 150],
          [780, 150],
        ],
        { kind: "model" }
      ) +
      arrow(
        [
          [700, 209],
          [740, 209],
          [740, 162],
          [780, 162],
        ],
        { kind: "model" }
      );
    b += text(10, 24, "TWO CLIENTS, ONE HOSTED MODEL · temperature 0.7 · top_p 0.8", {
      cls: "phase muted",
    });
    return svg(1000, 284, b, { title: "Two clients reach the same model" });
  };

  F.contextGap = (withNotes, fresh) => {
    const lane = (x, title, rows, answer, ok) => {
      let s = layer(x, 20, 480, 214, title, { kind: ok ? "sdk" : "" });
      s += text(x + 16, 62, "CONTEXT WINDOW", { cls: "phase muted" });
      rows.forEach(([lbl, kind], i) => {
        s +=
          `<rect x="${x + 16}" y="${72 + i * 42}" width="230" height="34" rx="8" class="box ${kind}" ${kind === "absent" ? 'style="stroke-dasharray:5 4"' : ""}/>` +
          text(x + 30, 94 + i * 42, lbl, { cls: kind === "absent" ? "note" : "n-sub" });
      });
      s += arrow(
        [
          [x + 246, 135],
          [x + 276, 135],
        ],
        { kind: "model" }
      );
      s += `<rect x="${x + 276}" y="78" width="188" height="114" rx="10" class="box ${ok ? "pooled" : ""}"/>`;
      wrap(answer, 24)
        .slice(0, 5)
        .forEach((l, k) => (s += text(x + 288, 102 + k * 18, l, { cls: "code-line", size: 12 })));
      return s;
    };
    let b = lane(
      10,
      "Call 1 · notes in the prompt",
      [
        ["system: evidence-only policy", "sdk"],
        ["Alice's note + update", "data"],
        ["the question", ""],
      ],
      withNotes || "Quantity: 120; Approval request: PO-1048 approved; Order status: not submitted",
      true
    );
    b += lane(
      510,
      "Call 2 · a new call, question only",
      [
        ["system: evidence-only policy", "sdk"],
        ["(no notes)", "absent"],
        ["the question", ""],
      ],
      fresh || "Quantity: unknown; Approval request: unknown; Order status: unknown",
      false
    );
    return svg(1000, 246, b, { title: "The prompt supplied the knowledge" });
  };

  F.agentLoop = () => {
    let b = node(20, 40, 200, 64, {
      icon: "book",
      title: "Assemble context",
      sub: "system + messages",
    });
    b += node(290, 40, 200, 64, {
      icon: "bulb",
      title: "Model picks a step",
      sub: "tool call or answer",
      kind: "model",
    });
    b += node(760, 40, 220, 64, { icon: "check", title: "Final answer", sub: "loop ends" });
    b += node(520, 170, 200, 64, {
      icon: "gear",
      title: "Run an allowed tool",
      sub: "read_reorder_policy",
      tsize: 14,
    });
    b += node(290, 170, 200, 64, {
      icon: "eye",
      title: "Observe the result",
      sub: "tool message added",
    });
    b += arrow(
      [
        [220, 72],
        [290, 72],
      ],
      { kind: "req" }
    );
    b += arrow(
      [
        [490, 72],
        [760, 72],
      ],
      { kind: "model", label: "done", at: [625, 64] }
    );
    b += arrow(
      [
        [440, 104],
        [440, 134],
        [620, 134],
        [620, 170],
      ],
      { kind: "read", label: "call", at: [530, 126] }
    );
    b += arrow(
      [
        [520, 202],
        [490, 202],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [390, 170],
        [390, 104],
      ],
      { kind: "model", dashed: true, label: "repeat", at: [384, 140], anchor: "end" }
    );
    b +=
      text(760, 190, "recursion_limit = 12", { cls: "mono-lbl" }) +
      text(760, 212, "A new agent starts empty:", { cls: "note" }) +
      text(760, 230, "tools don't make it remember.", { cls: "note" });
    return svg(1000, 250, b, { title: "The agent loop" });
  };

  /* -------------------------------------------------- Part 6 */

  F.lifecycle = () => {
    let b =
      text(20, 32, "AUTOMATIC · OAMP", { cls: "phase write" }) +
      text(270, 162, "REVIEWED · A PERSON", { cls: "phase ok" });
    b += node(20, 44, 210, 72, {
      icon: "chat",
      title: "Retain",
      sub: "add_messages()",
      sub2: "MESSAGE, verbatim",
    });
    b += node(270, 44, 210, 72, {
      icon: "sparkle",
      title: "Extract",
      sub: "background LLM",
      sub2: "candidate facts, preferences",
      kind: "model",
    });
    b += node(520, 44, 210, 72, {
      icon: "link",
      title: "Link",
      sub: "post-extraction",
      sub2: "inferred relations",
    });
    b += node(270, 174, 210, 72, {
      icon: "check",
      title: "Review",
      sub: "reviewed facts",
      sub2: "120 supersedes 80",
      kind: "okk",
    });
    b += node(780, 108, 200, 72, {
      icon: "search",
      title: "Recall",
      sub: "search · num_hops",
      sub2: "→ working context",
    });
    b +=
      arrow(
        [
          [230, 80],
          [270, 80],
        ],
        { kind: "write" }
      ) +
      arrow(
        [
          [480, 80],
          [520, 80],
        ],
        { kind: "write" }
      );
    b += arrow(
      [
        [730, 80],
        [755, 80],
        [755, 130],
        [780, 130],
      ],
      { kind: "read" }
    );
    b += arrow(
      [
        [375, 116],
        [375, 174],
      ],
      { kind: "ok", dashed: true, label: "a human checks", at: [381, 150], anchor: "start" }
    );
    b += arrow(
      [
        [480, 210],
        [755, 210],
        [755, 160],
        [780, 160],
      ],
      { kind: "read" }
    );
    return svg(1000, 262, b, { title: "The memory lifecycle" });
  };

  F.scopes = () => {
    let b = layer(10, 20, 980, 268, "One OAMP store · one prism account", { kind: "sdk" });
    b += layer(28, 56, 340, 214, "user_id = alice-<run>", { kind: "memory" });
    b +=
      `<rect x="44" y="90" width="308" height="166" rx="10" class="box"/>` +
      text(58, 112, "thread mugs-<run>", { cls: "mono-lbl" });
    b += pills(
      58,
      124,
      [
        ["messages", "t-message"],
        ["worksheet", "t-message"],
      ],
      { size: 11, h: 24 }
    );
    b += pills(
      58,
      156,
      [
        ["fact ×n", "t-fact"],
        ["preference", "t-preference"],
      ],
      { size: 11, h: 24 }
    );
    b += pills(
      58,
      188,
      [
        ["reviewed facts", "t-fact"],
        ["lesson", "t-guideline"],
      ],
      { size: 11, h: 24 }
    );
    b += text(58, 238, "the mug case and Alice's own notes", { cls: "note" });
    b += layer(386, 56, 250, 214, "user_id = bob-<run>", { kind: "memory" });
    b +=
      `<rect x="402" y="90" width="218" height="166" rx="10" class="box"/>` +
      text(416, 112, "thread returns-<run>", { cls: "mono-lbl" });
    b +=
      pills(416, 124, [["fact", "t-fact"]], { size: 11, h: 24 }) +
      text(416, 172, "RET-771 · tote bags", { cls: "note" }) +
      text(416, 190, "a different workflow", { cls: "note" });
    b += layer(654, 56, 318, 214, "user_id = None · shared", { kind: "muted" });
    b += pills(
      670,
      92,
      [
        ["guideline", "t-guideline"],
        ["guideline", "t-guideline"],
      ],
      { size: 11, h: 24 }
    );
    b += pills(
      670,
      124,
      [
        ["guideline", "t-guideline"],
        ["guideline", "t-guideline"],
      ],
      { size: 11, h: 24 }
    );
    b +=
      text(670, 176, "SOP-101 … SOP-104", { cls: "mono-lbl" }) +
      text(670, 196, "approved procedures,", { cls: "note" }) +
      text(670, 214, "reused by every case", { cls: "note" });
    b += text(
      500,
      306,
      "user_id and thread_id select evidence. This one database account can read all three — filters are not authorization.",
      { cls: "note", anchor: "middle" }
    );
    return svg(1000, 316, b, { title: "Users, threads and shared procedures" });
  };

  F.supersede = () => {
    let b = node(20, 56, 320, 84, {
      icon: "cross",
      title: "fact · INVALID (history)",
      sub: "initial proposal: reorder 80",
      sub2: "kept, not deleted",
      kind: "errk",
    });
    b += node(420, 56, 320, 84, {
      icon: "check",
      title: "fact · VALID (current)",
      sub: "approved 120 under PO-1048",
      sub2: "no supplier order submitted",
      kind: "okk",
    });
    b += arrow(
      [
        [420, 98],
        [340, 98],
      ],
      { kind: "write", label: "supersedes", at: [380, 90] }
    );
    b += text(380, 162, "link_records_async()", { cls: "mono-lbl", anchor: "middle" });
    b += node(790, 30, 190, 64, {
      icon: "search",
      title: "Search",
      sub: "include_invalid=False",
      sub2: "→ only the current fact",
    });
    b += node(790, 120, 190, 64, {
      icon: "link",
      title: "num_hops = 1",
      sub: "→ history alongside",
    });
    b +=
      arrow(
        [
          [740, 80],
          [790, 62],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [885, 94],
          [885, 120],
        ],
        { kind: "read" }
      );
    b += text(
      20,
      206,
      "Keep history without presenting it as current: the old proposal stays, marked invalid, reachable through its link.",
      { cls: "note" }
    );
    return svg(1000, 220, b, { title: "Supersede without erasing" });
  };

  /* -------------------------------------------------- Part 7 */

  F.offload = (r) => {
    const wc = r ? r.worksheet_chars : 1859,
      rc = r ? r.reference_chars : 164,
      sc = r ? r.source_chars : 2367,
      sm = r ? r.summary_chars : 330;
    let b = text(20, 24, "OFFLOAD · keep the detail, pass a pointer", { cls: "phase read" });
    b += node(20, 36, 220, 72, {
      icon: "doc",
      title: "Worksheet",
      sub: `30 lines · ${wc.toLocaleString()} chars`,
    });
    b += node(290, 36, 210, 72, {
      icon: "db",
      title: "Stored message",
      sub: "ttl_days = 1",
      sub2: "full detail kept",
    });
    b += node(550, 36, 200, 72, {
      icon: "link",
      title: "Reference",
      sub: `${rc} chars`,
      sub2: "message_id + note",
    });
    b += node(800, 36, 180, 72, {
      icon: "gear",
      title: "Agent",
      sub: "fetches detail",
      sub2: "only when asked",
    });
    b +=
      arrow(
        [
          [240, 72],
          [290, 72],
        ],
        { kind: "write" }
      ) +
      arrow(
        [
          [500, 72],
          [550, 72],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [750, 72],
          [800, 72],
        ],
        { kind: "read" }
      );
    b += text(20, 152, "COMPACT · a bounded summary, sources kept", { cls: "phase write" });
    b += node(20, 164, 220, 72, {
      icon: "chat",
      title: "Conversation",
      sub: `${r ? r.messages : 3} messages`,
      sub2: `${sc.toLocaleString()} chars`,
    });
    b += node(290, 164, 210, 72, {
      icon: "layers",
      title: "Summary",
      sub: "token_budget = 600",
      sub2: `${sm} chars`,
    });
    b += arrow(
      [
        [240, 200],
        [290, 200],
      ],
      { kind: "model" }
    );
    const max = Math.max(sc, wc),
      W = 410;
    [
      ["conversation", sc, "write"],
      ["summary", sm, "read"],
      ["worksheet", wc, "write"],
      ["reference", rc, "read"],
    ].forEach(([lbl, n, kind], i) => {
      const y = 166 + i * 18;
      b +=
        `<rect x="560" y="${y}" width="${Math.max(3, (n / max) * W)}" height="12" rx="4" class="bar-${kind}"/>` +
        text(556, y + 10, lbl, { cls: "mono-lbl", anchor: "end", size: 11 });
      b += text(566 + Math.max(3, (n / max) * W), y + 10, n.toLocaleString(), {
        cls: "mono-lbl",
        size: 11,
      });
    });
    return svg(1000, 250, b, { title: "Offload and compaction" });
  };

  F.memoryAgent = () => {
    let b = node(20, 112, 200, 80, {
      icon: "gear",
      title: "Agent loop",
      sub: "same model + factory",
      sub2: "new tools only",
      kind: "accent",
    });
    b += node(280, 50, 250, 72, {
      icon: "search",
      title: "recall_inventory",
      sub: "a query → three scopes",
      sub2: "chosen by the host",
    });
    b += node(280, 190, 250, 72, {
      icon: "doc",
      title: "inspect_stock_report",
      sub: "only report_reference.id",
      sub2: "anything else → refused",
    });
    b +=
      arrow(
        [
          [220, 140],
          [250, 140],
          [250, 86],
          [280, 86],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [220, 164],
          [250, 164],
          [250, 226],
          [280, 226],
        ],
        { kind: "read" }
      );
    const S = [
      ["Alice · fact · reviewed-fact", 26],
      ["Alice · guideline · reviewed-procedure", 78],
      ["shared (None) · guideline · approved-procedure", 130],
    ];
    S.forEach(([lbl, y]) => {
      b +=
        `<rect x="600" y="${y}" width="380" height="40" rx="9" class="box pooled"/>` +
        text(616, y + 25, lbl, { cls: "mono-lbl" });
      b += arrow(
        [
          [530, 86],
          [565, 86],
          [565, y + 20],
          [600, y + 20],
        ],
        { kind: "read", end: true }
      );
    });
    b +=
      `<rect x="600" y="206" width="380" height="40" rx="9" class="box"/>` +
      icon("lock", 612, 216, 16, "muted") +
      text(636, 231, "MESSAGE · stock-history worksheet", { cls: "mono-lbl" });
    b += arrow(
      [
        [530, 226],
        [600, 226],
      ],
      { kind: "read" }
    );
    b += text(500, 282, "The host — not the model — decides which evidence each tool can reach.", {
      cls: "note",
      anchor: "middle",
    });
    return svg(1000, 294, b, { title: "Memory tools on the same loop" });
  };

  /* -------------------------------------------------- Part 8 */

  F.retrieval = (ev, pr) => {
    let b = node(20, 70, 200, 64, { icon: "chat", title: "Question", sub: "e.g. reorder checks" });
    b += node(260, 70, 200, 64, {
      icon: "search",
      title: "Vector search",
      sub: "shared guidelines",
    });
    b +=
      arrow(
        [
          [220, 102],
          [260, 102],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [460, 102],
          [500, 102],
        ],
        { kind: "read" }
      );
    b +=
      `<rect x="500" y="20" width="240" height="172" rx="10" class="box"/>` +
      text(516, 42, "RETURNED ORDER", { cls: "phase muted" });
    const rows = (ev && ev.results) || [
      { rank: 1, id: "sop-reorder" },
      { rank: 2, id: "sop-count" },
      { rank: 3, id: "sop-delivery" },
    ];
    rows.slice(0, 4).forEach((r, i) => {
      const hit = ev && r.id === ev.expected_id;
      b += text(516, 70 + i * 30, `${r.rank} · ${String(r.id).replace(/-[0-9a-f]{10}$/, "")}`, {
        cls: hit ? "a-lbl ok" : "mono-lbl",
      });
    });
    if (ev)
      b += pills(516, 160, [[`hit@3 = ${ev["hit@3"]}`, ev["hit@3"] ? "read" : "write"]], {
        size: 11,
        h: 22,
      });
    b += node(790, 30, 190, 64, {
      icon: "scissors",
      title: "LLM pruning",
      sub: "keep or discard each",
      kind: "model",
    });
    b += node(790, 128, 190, 64, {
      icon: "check",
      title: "Smaller context",
      sub: pr ? `${pr.unpruned.length} → ${pr.pruned.length} records` : "fewer, more useful",
    });
    b +=
      arrow(
        [
          [740, 70],
          [790, 62],
        ],
        { kind: "model" }
      ) +
      arrow(
        [
          [885, 94],
          [885, 128],
        ],
        { kind: "read" }
      );
    b += text(
      20,
      222,
      "Similarity is not usefulness: inspect what recall returns, in order, before deciding what the model should see.",
      { cls: "note" }
    );
    return svg(1000, 236, b, { title: "Retrieve, inspect, prune" });
  };

  F.events = (order) => {
    let b = layer(20, 24, 960, 168, "agent_memory · search", { kind: "sdk" });
    b += layer(60, 62, 880, 112, "memory_store · search", { kind: "memory" });
    b += node(100, 100, 800, 52, {
      icon: "bolt",
      title: "embedder · started → completed",
      sub: "the query is embedded in Oracle",
      tsize: 14,
    });
    const seq =
      order && order.length
        ? order
        : [
            "agent_memory · …search.started",
            "memory_store · …search.started",
            "embedder · started",
            "embedder · completed",
            "memory_store · …search.completed",
            "agent_memory · …search.completed",
          ];
    b += text(
      20,
      214,
      `${seq.length} events, in this order — names and counts only, no prompt or record content:`,
      { cls: "note" }
    );
    b += text(20, 234, seq.map((s, i) => `${i + 1} ${s.split(" · ")[1] || s}`).join("   "), {
      cls: "mono-lbl",
      size: 11,
    });
    return svg(1000, 246, b, { title: "Operation events for one search" });
  };

  F.contextCard = () => {
    let b = text(20, 14, "EVIDENCE, LABELLED BY TRUST", { cls: "phase muted" });
    b += node(20, 24, 290, 64, {
      icon: "check",
      title: "Reviewed current fact",
      sub: "authoritative",
      kind: "okk",
    });
    b += node(20, 104, 290, 64, {
      icon: "star",
      title: "Approved procedures",
      sub: "shared guidelines",
    });
    b += node(20, 184, 290, 72, {
      icon: "book",
      title: "Context card",
      sub: "unverified conversation context",
      sub2: "budget 1,600 for relevant records",
    });
    b +=
      `<rect x="370" y="76" width="230" height="128" rx="10" class="codebox"/>` +
      text(386, 100, "evidence = {", { cls: "code-line" });
    b +=
      text(398, 124, "reviewed_current_fact", { cls: "code-line", size: 12 }) +
      text(398, 146, "approved_procedures", { cls: "code-line", size: 12 }) +
      text(398, 168, "unverified_conversation…", { cls: "code-line", size: 12 }) +
      text(386, 192, "}", { cls: "code-line" });
    b +=
      arrow(
        [
          [310, 56],
          [340, 56],
          [340, 120],
          [370, 120],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [310, 136],
          [370, 136],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [310, 220],
          [340, 220],
          [340, 160],
          [370, 160],
        ],
        { kind: "read" }
      );
    b += node(650, 104, 150, 72, {
      icon: "bolt",
      title: "OAMP Llm",
      sub: "handover prompt",
      kind: "model",
    });
    b += node(840, 104, 140, 72, {
      icon: "doc",
      title: "Draft",
      sub: "< 120 words",
      sub2: "→ review gate",
    });
    b +=
      arrow(
        [
          [600, 140],
          [650, 140],
        ],
        { kind: "model" }
      ) +
      arrow(
        [
          [800, 140],
          [840, 140],
        ],
        { kind: "write" }
      );
    return svg(1000, 266, b, { title: "Assemble the next shift's working context" });
  };

  /* -------------------------------------------------- Part 9 */

  F.reviewGate = () => {
    let b = text(
      20,
      22,
      "THE MODEL DRAFTS; IT NEVER APPROVES. CHANGING ONE CHARACTER INVALIDATES THE PHRASE.",
      { cls: "phase muted" }
    );
    b += node(20, 50, 170, 64, { icon: "doc", title: "Draft", sub: "from Part 8.4" });
    b += node(230, 50, 210, 64, {
      icon: "key",
      title: "sha256(run, draft)",
      sub: "binds approval to text",
      tsize: 14,
    });
    b += node(480, 50, 190, 64, {
      icon: "user",
      title: "APPROVE <digest>",
      sub: "a person reviews",
      tsize: 13.5,
    });
    b += node(710, 50, 270, 64, { icon: "lock", title: "Host compares", sub: "outside the agent" });
    b +=
      arrow(
        [
          [190, 82],
          [230, 82],
        ],
        { kind: "req" }
      ) +
      arrow(
        [
          [440, 82],
          [480, 82],
        ],
        { kind: "req" }
      ) +
      arrow(
        [
          [670, 82],
          [710, 82],
        ],
        { kind: "req" }
      );
    b += node(710, 150, 130, 60, {
      icon: "check",
      title: "match",
      sub: "save the draft",
      kind: "okk",
    });
    b += node(850, 150, 130, 60, {
      icon: "cross",
      title: "no match",
      sub: "blocked, no I/O",
      kind: "errk",
    });
    b +=
      arrow(
        [
          [775, 114],
          [775, 150],
        ],
        { kind: "ok" }
      ) +
      arrow(
        [
          [915, 114],
          [915, 150],
        ],
        { kind: "err" }
      );
    b +=
      text(20, 168, "Supplier orders and stock adjustments stay outside", { cls: "note" }) +
      text(20, 186, "the agent entirely: its tools are read-only.", { cls: "note" });
    return svg(1000, 222, b, { title: "Review an action separately from generating it" });
  };

  F.reuse = () => {
    let b = node(20, 40, 270, 72, {
      icon: "box",
      title: "Case facts",
      sub: "120 · PO-1048 · RESTOCK-101",
      sub2: "stay with this case",
    });
    b += node(350, 40, 290, 72, {
      icon: "check",
      title: "Reviewed lesson",
      sub: "guideline — no quantities, no IDs",
      sub2: "version 1",
      kind: "okk",
    });
    b += node(700, 40, 280, 72, {
      icon: "gear",
      title: "Next product's agent",
      sub: "recall_procedure only",
    });
    b += node(700, 140, 280, 56, {
      icon: "check",
      title: "Checklist",
      sub: "the method, not old values",
    });
    b += arrow(
      [
        [290, 76],
        [350, 76],
      ],
      { kind: "ok", dashed: true, label: "generalise", at: [320, 68] }
    );
    b +=
      arrow(
        [
          [640, 76],
          [700, 76],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [840, 112],
          [840, 140],
        ],
        { kind: "model" }
      );
    b +=
      text(20, 170, "Improvement is a reviewed feedback loop: it updates", { cls: "note" }) +
      text(20, 188, "retrievable knowledge, not the model's weights.", { cls: "note" });
    return svg(1000, 210, b, { title: "Reuse a reviewed lesson" });
  };

  F.ttl = (t, c) => {
    let b = node(20, 70, 210, 72, {
      icon: "clock",
      title: "Record",
      sub: "ttl_days = 0",
      sub2: "expires immediately",
    });
    b += node(290, 24, 290, 64, {
      icon: "search",
      title: "Search",
      sub: t ? `→ ${t.search_hits} hits: hidden from recall` : "→ hidden from recall",
    });
    b += node(290, 120, 290, 64, {
      icon: "db",
      title: "SQL COUNT(*)",
      sub: t ? `→ ${t.row_count} row: still stored` : "→ the row still exists",
    });
    b +=
      arrow(
        [
          [230, 96],
          [290, 56],
        ],
        { kind: "read" }
      ) +
      arrow(
        [
          [230, 116],
          [290, 152],
        ],
        { kind: "data" }
      );
    b += node(640, 70, 340, 72, {
      icon: "trash",
      title: "delete_thread_async ×2",
      sub: c
        ? `this run's threads → ${c.all_zero ? "0 rows" : "rows left"}`
        : "this run's two threads → 0 rows",
      sub2: c
        ? `${c.shared_procedures_kept} shared procedures keep their TTL`
        : "shared procedures keep their TTL",
    });
    b += arrow(
      [
        [580, 152],
        [610, 152],
        [610, 106],
        [640, 106],
      ],
      { kind: "write" }
    );
    b += text(
      20,
      214,
      "Expired is not erased. Zero live rows is not erasure from backups, replicas or logs.",
      { cls: "note" }
    );
    return svg(1000, 226, b, { title: "Expiration is not erasure" });
  };

  F.todoMap = () => {
    const P = [
      ["4", "#/part4", [[1, "context window"]]],
      ["5", "#/part5", [[2, "agent loop"]]],
      [
        "6",
        "#/part6",
        [
          [3, "embed in Oracle"],
          [4, "planner labels"],
          [5, "background extraction"],
          [6, "supersede"],
          [7, "graph recall"],
        ],
      ],
      [
        "7",
        "#/part7",
        [
          [8, "bounded recall"],
          [9, "offload worksheet"],
          [10, "recall tool"],
          [11, "memory aware loop"],
        ],
      ],
      [
        "8",
        "#/part8",
        [
          [12, "pruning"],
          [13, "observability"],
          [14, "context card"],
        ],
      ],
      [
        "9",
        "#/part9",
        [
          [15, "scopes ≠ permissions"],
          [16, "review before write"],
          [17, "reusable lesson"],
        ],
      ],
    ];
    let b = "";
    P.forEach(([part, href, todos], i) => {
      const x = 10 + i * 166;
      b += text(x, 22, `PART ${part}`, { cls: "phase read" });
      todos.forEach(([n, topic], k) => {
        b +=
          `<a href="${n === 3 ? "#/part3" : href}" class="dg-link"><g class="node"><rect x="${x}" y="${34 + k * 64}" width="154" height="54" rx="10"/>` +
          text(x + 12, 56 + k * 64, `TODO ${n}`, { cls: "num-badge", size: 13 }) +
          text(x + 12, 75 + k * 64, topic, { cls: "n-sub", size: 12 }) +
          "</g></a>";
      });
    });
    return svg(1000, 360, b, { title: "The 17 TODOs by Part" });
  };
})();
