/* Draws one person's blood relatives. Recentres on click, deep-links on ?p=.
   Every line takes the colour of the evidence the dossier recorded for it. */
(function () {
  var P = window.__BLOOD || {}, START = window.__START;
  var svg = document.getElementById("bl-svg");
  var input = document.getElementById("who");
  var none = document.getElementById("bl-none");
  var list = document.getElementById("bl-names");
  if (!svg || !P[START]) return;

  var NS = "http://www.w3.org/2000/svg";
  var W = 940, BOX = 168, BH = 44, GAPX = 16, LANE = 116;
  var STROKE = { read: ["var(--accent-2,#5c8a5c)", "0"], line: ["var(--accent-2,#5c8a5c)", "0"],
                 index: ["var(--accent)", "0"], tree: ["var(--ochre,#8a7f5c)", "6 4"] };

  /* Folding, kept the same shape as the kit's search so the two agree about
     what a reader typing with no accents and no punctuation means. */
  function fold(x) {
    return String(x == null ? "" : x).normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }
  function squash(x) { return fold(x).replace(/[^a-z0-9]+/g, ""); }

  var ALL = Object.keys(P).map(function (s) {
    return { slug: s, name: P[s].name, f: fold(P[s].name), q: squash(P[s].name),
             deg: P[s].parents.length + P[s].children.length + P[s].siblings.length };
  }).sort(function (a, b) { return a.name.localeCompare(b.name); });

  function search(v) {
    var f = fold(v.trim()), q = squash(v);
    if (!f) return [];
    return ALL.filter(function (p) { return p.f.indexOf(f) > -1 || (q && p.q.indexOf(q) > -1); })
      .sort(function (a, b) {
        /* a name that STARTS with what was typed first, then the best connected,
           because a person with no relatives draws an empty chart */
        var as = a.f.indexOf(f) === 0 ? 0 : 1, bs = b.f.indexOf(f) === 0 ? 0 : 1;
        return as - bs || b.deg - a.deg || a.name.localeCompare(b.name);
      });
  }

  function el(n, a, t) {
    var e = document.createElementNS(NS, n);
    for (var k in a) e.setAttribute(k, a[k]);
    if (t != null) e.textContent = t;
    return e;
  }
  function clip(s, n) { return s && s.length > n ? s.slice(0, n - 1) + "…" : (s || ""); }

  function row(items, y, lane) {
    // centre a row of boxes on the canvas
    var n = items.length;
    if (!n) return [];
    var total = n * BOX + (n - 1) * GAPX;
    var x0 = Math.max(12, (W - total) / 2);
    return items.map(function (it, i) {
      return { it: it, x: x0 + i * (BOX + GAPX), y: y, lane: lane };
    });
  }

  function draw(slug) {
    var me = P[slug];
    if (!me) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    var parents = me.parents.filter(function (p) { return p.slug; });
    var sibs = me.siblings.filter(function (p) { return p.slug; });
    var kids = me.children;
    var rows = [];
    var y = 34;
    if (parents.length) { rows = rows.concat(row(parents, y, "parents")); y += LANE; }
    var mid = [{ slug: slug, name: me.name, dt: me.dt, self: true }];
    sibs.slice(0, 3).forEach(function (s) { mid.unshift(s); });
    if (me.spouse) mid.push({ slug: null, name: me.spouse, dt: "", spouse: true });
    rows = rows.concat(row(mid, y, sibs.length ? "this person, with brothers and sisters" : "this person"));
    var selfY = y; y += LANE;
    if (kids.length) rows = rows.concat(row(kids.slice(0, 5), y, "children"));

    var H = y + (kids.length ? BH + 34 : 20);
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("height", H);

    var selfBox = rows.find(function (r) { return r.it.self; });

    // edges first, so boxes sit on top
    rows.forEach(function (r) {
      if (r.it.self || r.lane === "this person" && !r.it.spouse) return;
      if (r.it.spouse) {
        svg.appendChild(el("path", { d: "M" + (selfBox.x + BOX) + "," + (selfY + BH / 2) +
          " L" + r.x + "," + (r.y + BH / 2), stroke: "var(--ink-3)", "stroke-width": 1.5,
          "stroke-dasharray": "5 4", fill: "none" }));
        return;
      }
      var s = STROKE[r.it.via] || STROKE.tree;
      var a, b;
      if (r.lane === "parents") { a = [r.x + BOX / 2, r.y + BH]; b = [selfBox.x + BOX / 2, selfY]; }
      else if (r.lane === "children") { a = [selfBox.x + BOX / 2, selfY + BH]; b = [r.x + BOX / 2, r.y]; }
      else { a = [r.x + BOX, r.y + BH / 2]; b = [selfBox.x, selfY + BH / 2]; }
      svg.appendChild(el("path", {
        d: "M" + a[0] + "," + a[1] + " C" + a[0] + "," + ((a[1] + b[1]) / 2) +
           " " + b[0] + "," + ((a[1] + b[1]) / 2) + " " + b[0] + "," + b[1],
        stroke: s[0], "stroke-width": 2.2, "stroke-dasharray": s[1], fill: "none"
      }));
    });

    var lanes = {};
    rows.forEach(function (r) { if (!lanes[r.lane]) { lanes[r.lane] = r.y; } });
    Object.keys(lanes).forEach(function (L) {
      svg.appendChild(el("text", { x: 12, y: lanes[L] - 10, class: "bl-lane" }, L));
    });

    rows.forEach(function (r) {
      var g = el("g", { class: "bl-node" + (r.it.self ? " is-self" : "") + (r.it.spouse ? " is-spouse" : "") });
      if (r.it.slug && !r.it.self) {
        g.setAttribute("tabindex", "0");
        g.setAttribute("role", "button");
        g.addEventListener("click", function () { go(r.it.slug); });
        g.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(r.it.slug); } });
      } else if (!r.it.slug) g.setAttribute("class", g.getAttribute("class") + " is-flat");
      g.appendChild(el("rect", { x: r.x, y: r.y, width: BOX, height: BH, rx: 5 }));
      g.appendChild(el("text", { x: r.x + 12, y: r.y + 19 }, clip(r.it.name, 24)));
      g.appendChild(el("text", { x: r.x + 12, y: r.y + 34, class: "bl-dt" },
        r.it.spouse ? "married in" : clip(r.it.dt || "", 26)));
      svg.appendChild(g);
    });
  }

  function go(slug) {
    if (!P[slug]) return;
    draw(slug);
    input.value = P[slug].name;
    history.replaceState(null, "", "?p=" + encodeURIComponent(slug));
  }

  /* The first version of this listened for "change" and demanded the reader
     type a person's whole name exactly. Typing a surname did nothing at all,
     silently — and the surname is spelt Defranceschi in these registers and
     Defranceski on the modern side of the family, so even the obvious guess
     missed. It is a search now. */
  var results = document.createElement("div");
  results.className = "bl-hits";
  input.parentNode.insertBefore(results, none);

  function render(v) {
    var hits = search(v);
    results.textContent = "";
    none.hidden = !v.trim() || hits.length > 0;
    if (!v.trim()) return;
    hits.slice(0, 10).forEach(function (h) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "bl-hit";
      b.innerHTML = "";
      var n = document.createElement("span");
      n.className = "bl-hit-n"; n.textContent = h.name;
      var d = document.createElement("span");
      d.className = "bl-hit-d";
      d.textContent = h.deg ? h.deg + (h.deg === 1 ? " relative" : " relatives") : "no relatives yet";
      b.appendChild(n); b.appendChild(d);
      b.addEventListener("click", function () { go(h.slug); results.textContent = ""; });
      results.appendChild(b);
    });
    if (hits.length > 10) {
      var more = document.createElement("div");
      more.className = "bl-more";
      more.textContent = hits.length - 10 + " more — keep typing";
      results.appendChild(more);
    }
  }

  var t;
  input.addEventListener("input", function () {
    clearTimeout(t);
    var v = input.value;
    t = setTimeout(function () { render(v); }, 120);
  });
  input.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    var hits = search(input.value);
    if (hits.length) { go(hits[0].slug); results.textContent = ""; }
  });

  var q = new URLSearchParams(location.search).get("p");
  go(P[q] ? q : START);
})();
