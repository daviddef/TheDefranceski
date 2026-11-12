#!/usr/bin/env python3
"""Every entry of the header menu, old build against new: where each address stood and where it stands now (12 November 2026, the menu regroup).
    python3 scripts/menu-moves.py BEFORE_DIST AFTER_DIST [OUT.md]
Reads the <nav class="topnav"> of the home page of each build. Exit 1 if an address that was in the menu is in no menu now and is not
listed in DROPPED below with its reason."""
import re, sys, html

# an address that left the menu on purpose, and why
DROPPED = {}


def menu(dist):
    t = open(dist + "/index.html", encoding="utf-8").read()
    nav = t[t.index('<nav class="topnav"'):]
    nav = nav[:nav.index("</nav>")]
    out = []   # (menu, group-or-sub, href, label)
    for m in re.finditer(r'<details class="menu">(.*?)</details>', nav, re.S):
        body = m.group(1)
        label = html.unescape(re.search(r"<summary>(.*?)</summary>", body, re.S).group(1))
        grp = ""
        for tok in re.finditer(r'<(?:div class="pg"|a [^>]*href="([^"]+)"[^>]*>(.*?)</a>|span class="ps[^"]*">(.*?)</span>)', body, re.S):
            if tok.group(0).startswith('<div class="pg"'):
                grp = ""
            elif tok.group(3) is not None:
                grp = html.unescape(tok.group(3))
            else:
                href, txt = tok.group(1), html.unescape(re.sub(r"<[^>]+>", "", tok.group(2)))
                if "ph" in tok.group(0)[:40]:
                    grp = txt
                    out.append((label, grp, href, txt + "  (group heading)"))
                else:
                    out.append((label, grp, href, txt))
    return out


def main():
    b, a = menu(sys.argv[1]), menu(sys.argv[2])
    bh = {}
    for m, g, h, l in b:
        bh.setdefault(h, []).append((m, g, l))
    ah = {}
    for m, g, h, l in a:
        ah.setdefault(h, []).append((m, g, l))
    L = ["# The menu, before and after", "", "| address | was | now |", "|---|---|---|"]
    bad = 0
    for h in list(dict.fromkeys([x[2] for x in b] + [x[2] for x in a])):
        was = "; ".join("%s%s: %s" % (m, " / " + g if g else "", l) for m, g, l in bh.get(h, [])) or "—"
        now = "; ".join("%s%s: %s" % (m, " / " + g if g else "", l) for m, g, l in ah.get(h, [])) or "—"
        if h in bh and h not in ah and h not in DROPPED:
            now = "**not in the menu**"
            bad += 1
        if was != now:
            L.append("| `%s` | %s | %s |" % (h, was, now))
    L += ["", "%d address(es) were in the menu and are in none now without a stated reason." % bad]
    out = "\n".join(L) + "\n"
    if len(sys.argv) > 3:
        open(sys.argv[3], "w", encoding="utf-8").write(out)
    print(out)
    sys.exit(1 if bad else 0)


main()
