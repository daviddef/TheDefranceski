/* Everyone one person is related to — not a card of their immediate family.
   Parents, children, brothers and sisters, and through them aunts, uncles,
   cousins and their children, as far as the archive's links reach. Laid out by
   generation, scrollable in both directions, every line in the colour of the
   record behind it. */
(function () {
  var P = window.__BLOOD || {}, START = window.__START;
  var svg = document.getElementById("bl-svg");
  var input = document.getElementById("who");
  var none = document.getElementById("bl-none");
  var stage = document.getElementById("bl-stage");
  var summary = document.getElementById("bl-summary");
  if (!svg || !P[START]) return;

  var NS = "http://www.w3.org/2000/svg";
  var BOX = 150, BH = 42, GAPX = 14, LANE = 96, PAD = 20;
  var STROKE = { read: ["var(--accent-2,#5c8a5c)", "0"], line: ["var(--accent-2,#5c8a5c)", "0"],
                 index: ["var(--accent)", "0"], tree: ["var(--ochre,#8a7f5c)", "6 4"] };

  function fold(x) {
    return String(x == null ? "" : x).normalize("NFD")
      .replace(/[̀-ͯ]/g, "").toLowerCase();
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
        var as = a.f.indexOf(f) === 0 ? 0 : 1, bs = b.f.indexOf(f) === 0 ? 0 : 1;
        return as - bs || b.deg - a.deg || a.name.localeCompare(b.name);
      });
  }

  var kids = function (s) { return (P[s].children || []).filter(function (c) { return c.slug; }); };
  var pars = function (s) { return (P[s].parents || []).filter(function (c) { return c.slug; }); };
  var sibs = function (s) { return (P[s].siblings || []).filter(function (c) { return c.slug; }); };

  /* everyone reachable by blood, with their generation relative to the root */
  function household(root) {
    var gen = {}, order = [];
    gen[root] = 0;
    var q = [root];
    while (q.length) {
      var x = q.shift();
      order.push(x);
      pars(x).forEach(function (p) { if (!(p.slug in gen)) { gen[p.slug] = gen[x] - 1; q.push(p.slug); } });
      kids(x).forEach(function (c) { if (!(c.slug in gen)) { gen[c.slug] = gen[x] + 1; q.push(c.slug); } });
      sibs(x).forEach(function (s) { if (!(s.slug in gen)) { gen[s.slug] = gen[x]; q.push(s.slug); } });
    }
    return { gen: gen, order: order };
  }

  /* how the archive would describe this person to the one in the middle */
  function ancestors(s) {
    var d = {}, q = [[s, 0]];
    while (q.length) {
      var it = q.shift(), x = it[0], n = it[1];
      if (x in d && d[x] <= n) continue;
      d[x] = n;
      if (n > 8) continue;
      pars(x).forEach(function (p) { q.push([p.slug, n + 1]); });
    }
    return d;
  }
  var ORD = ["", "great-", "great-great-", "3× great-", "4× great-", "5× great-", "6× great-"];
  function updown(n, word) { return (ORD[Math.max(0, n - (word === "parent" ? 1 : 1))] || (n + "× ") ) + word; }

  function kin(root, x) {
    if (x === root) return "this person";
    var A = ancestors(root), B = ancestors(x), best = null;
    for (var k in B) if (k in A) {
      var tot = A[k] + B[k];
      if (!best || tot < best.t) best = { t: tot, a: A[k], b: B[k] };
    }
    /* a sibling link with no shared parent recorded still means a sibling */
    if (!best) return sibs(root).some(function (s) { return s.slug === x; }) ? "brother or sister" : "related";
    var up = best.a, down = best.b;          // up: root→ancestor, down: x→ancestor
    if (down === 0) return up === 1 ? "parent" : up === 2 ? "grandparent" : updown(up, "grandparent");
    if (up === 0) return down === 1 ? "child" : down === 2 ? "grandchild" : updown(down, "grandchild");
    if (up === 1 && down === 1) return "brother or sister";
    if (down === 1) return up === 2 ? "aunt or uncle" : updown(up - 1, "great-aunt or uncle");
    if (up === 1) return down === 2 ? "niece or nephew" : updown(down - 1, "great-niece or nephew");
    var deg = Math.min(up, down) - 1, rem = Math.abs(up - down);
    var name = deg === 1 ? "first cousin" : deg === 2 ? "second cousin" : deg + "rd cousin";
    return rem ? name + (rem === 1 ? ", once removed" : rem === 2 ? ", twice removed" : ", " + rem + "× removed") : name;
  }

  function draw(root) {
    var me = P[root];
    if (!me) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    var h = household(root), gen = h.gen;
    var byGen = {};
    Object.keys(gen).forEach(function (s) { (byGen[gen[s]] = byGen[gen[s]] || []).push(s); });
    var gens = Object.keys(byGen).map(Number).sort(function (a, b) { return a - b; });

    /* order each generation so that children sit near their parents */
    var pos = {};
    gens.forEach(function (gi, row) {
      var list = byGen[gi];
      if (row > 0) {
        list.sort(function (a, b) {
          var pa = pars(a).map(function (p) { return pos[p.slug]; }).filter(function (v) { return v != null; });
          var pb = pars(b).map(function (p) { return pos[p.slug]; }).filter(function (v) { return v != null; });
          var ma = pa.length ? pa.reduce(function (s, v) { return s + v; }, 0) / pa.length : 1e9;
          var mb = pb.length ? pb.reduce(function (s, v) { return s + v; }, 0) / pb.length : 1e9;
          return ma - mb || P[a].name.localeCompare(P[b].name);
        });
      } else {
        list.sort(function (a, b) { return P[a].name.localeCompare(P[b].name); });
      }
      list.forEach(function (s, i) { pos[s] = i; });
    });

    /* a married person takes two boxes' worth of room, their own and their
       husband's or wife's, so the rows have to be measured rather than counted */
    var wide = function (s) { return BOX + (P[s].spouse ? GAPX + BOX : 0); };
    var rowW = function (gi) {
      return byGen[gi].reduce(function (t, s) { return t + wide(s); }, 0)
             + (byGen[gi].length - 1) * GAPX * 2;
    };
    var W = Math.max(640, PAD * 2 + Math.max.apply(null, gens.map(rowW)));
    var H = PAD * 2 + gens.length * LANE;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);

    var xy = {};
    gens.forEach(function (gi, row) {
      var list = byGen[gi];
      var x = (W - rowW(gi)) / 2;
      list.forEach(function (s) {
        xy[s] = { x: x, y: PAD + row * LANE };
        x += wide(s) + GAPX * 2;
      });
    });

    function edge(a, b, via) {
      var A = xy[a], B = xy[b];
      if (!A || !B) return;
      var s = STROKE[via] || STROKE.tree;
      var ax = A.x + BOX / 2, ay = A.y + BH, bx = B.x + BOX / 2, by = B.y;
      svg.appendChild(el("path", {
        d: "M" + ax + "," + ay + " C" + ax + "," + (ay + LANE * 0.35) +
           " " + bx + "," + (by - LANE * 0.35) + " " + bx + "," + by,
        stroke: s[0], "stroke-width": 2, "stroke-dasharray": s[1], fill: "none", "stroke-opacity": ".85"
      }));
    }
    function el(n, a, t) {
      var e = document.createElementNS(NS, n);
      for (var k in a) e.setAttribute(k, a[k]);
      if (t != null) e.appendChild(document.createTextNode(t));
      return e;
    }
    function clip(s, n) { return s && s.length > n ? s.slice(0, n - 1) + "…" : (s || ""); }

    Object.keys(gen).forEach(function (s) {
      kids(s).forEach(function (c) { if (c.slug in gen) edge(s, c.slug, c.via); });
    });

    Object.keys(gen).forEach(function (s) {
      var p = xy[s], isMe = s === root;
      var g = el("g", { class: "bl-node" + (isMe ? " is-self" : "") });
      if (!isMe) {
        g.setAttribute("tabindex", "0");
        g.setAttribute("role", "button");
        g.addEventListener("click", function () { go(s); });
        g.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(s); } });
      }
      g.appendChild(el("rect", { x: p.x, y: p.y, width: BOX, height: BH, rx: 5 }));
      g.appendChild(el("text", { x: p.x + 10, y: p.y + 17 }, clip(P[s].name, 22)));
      g.appendChild(el("text", { x: p.x + 10, y: p.y + 31, class: "bl-dt" },
        clip(P[s].dt || kin(root, s), 26)));
      g.appendChild(el("title", {}, P[s].name + (P[s].dt ? ", " + P[s].dt : "") + " — " + kin(root, s)));
      svg.appendChild(g);

      /* The wife or husband, beside them, joined by a marriage line. Drawn
         differently on purpose: they are not blood, and this page is about
         blood — but leaving them out makes a family look like a list of
         single men. */
      if (P[s].spouse) {
        var sx = p.x + BOX + GAPX;
        svg.appendChild(el("path", {
          d: "M" + (p.x + BOX) + "," + (p.y + BH / 2) + " L" + sx + "," + (p.y + BH / 2),
          stroke: "var(--ink-3)", "stroke-width": 1.5, "stroke-dasharray": "5 4", fill: "none"
        }));
        var sg = el("g", { class: "bl-node is-spouse" });
        sg.appendChild(el("rect", { x: sx, y: p.y, width: BOX, height: BH, rx: 5 }));
        sg.appendChild(el("text", { x: sx + 10, y: p.y + 17 }, clip(P[s].spouse, 22)));
        sg.appendChild(el("text", { x: sx + 10, y: p.y + 31, class: "bl-dt" },
          clip(P[s].spouseDt ? "b. " + P[s].spouseDt : "married in", 26)));
        sg.appendChild(el("title", {}, P[s].spouse + " — married " + P[s].name));
        svg.appendChild(sg);
      }
    });

    var n = Object.keys(gen).length;
    summary.textContent = n === 1
      ? "No relative of " + me.name + " is recorded here yet."
      : n + " people, across " + gens.length + " generations — everyone this archive can join to "
        + me.name + " by blood.";
    var box = xy[root];
    if (box) stage.scrollLeft = Math.max(0, box.x + BOX / 2 - stage.clientWidth / 2);
  }

  function go(slug) {
    if (!P[slug]) return;
    draw(slug);
    input.value = P[slug].name;
    history.replaceState(null, "", "?p=" + encodeURIComponent(slug));
  }

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
      b.type = "button"; b.className = "bl-hit";
      var nm = document.createElement("span"); nm.className = "bl-hit-n"; nm.textContent = h.name;
      var d = document.createElement("span"); d.className = "bl-hit-d";
      d.textContent = h.deg ? h.deg + (h.deg === 1 ? " relative" : " relatives") : "no relatives yet";
      b.appendChild(nm); b.appendChild(d);
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
    clearTimeout(t); var v = input.value;
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
