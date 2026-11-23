/* Diagrams: a small inline-SVG toolkit (layers, nodes, pills, arrows); the
   appbook's figures live in diagrams.js. Colours come from CSS variables (--d-*), so every figure
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
    box: '<path d="m3 7.5 9-4.5 9 4.5v9L12 21l-9-4.5z"/><path d="m3 7.5 9 4.5 9-4.5M12 12v9"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    scissors:
      '<circle cx="6" cy="6.5" r="2.6"/><circle cx="6" cy="17.5" r="2.6"/><path d="M8.2 8 20 18M8.2 16 20 6"/>',
    key: '<circle cx="8" cy="14" r="4.5"/><path d="M11.3 10.8 20 2.5M16.5 6l2.5 2.5M14 8.5l2 2"/>',
    user: '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20c.8-4 3.8-6 7.5-6s6.7 2 7.5 6"/>',
    refresh:
      '<path d="M20 11a8 8 0 0 0-14.5-4.5L3 9M3 4v5h5M4 13a8 8 0 0 0 14.5 4.5L21 15M21 20v-5h-5"/>',
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

  /* Figures are defined in diagrams.js. */
  const F = {};

  return { F, svg, node, arrow, layer, pills, pill, text, icon, box, tw };
})();
