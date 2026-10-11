#!/usr/bin/env python3
"""The contents of /gologorica-line/ must name every section on it."""
import json, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
ast = (ROOT/"site/src/pages/gologorica-line.astro").read_text()
try:
    toc = json.loads((ROOT/"site/src/data/gologorica-toc.json").read_text())["rows"]
except FileNotFoundError:
    print("FAIL  golo-toc: gologorica-toc.json does not exist — run scripts/build-golo-toc.py"); sys.exit(1)
page = re.findall(r'<h2 id="([A-Za-z0-9_-]+)"', ast)
have = [r["id"] for r in toc]
if page != have:
    miss = [i for i in page if i not in have]; extra = [i for i in have if i not in page]
    print("FAIL  golo-toc: contents and page disagree — run scripts/build-golo-toc.py")
    if miss:  print("        on the page, not in the contents: " + ", ".join(miss))
    if extra: print("        in the contents, not on the page: " + ", ".join(extra))
    if not miss and not extra: print("        same sections, different order")
    sys.exit(1)
g = json.loads((ROOT/"site/src/data/gologorica.json").read_text())
stale = [r["id"] for r in toc if g.get(r["id"], {}).get("heading", r["heading"]) != r["heading"]]
if stale:
    print("FAIL  golo-toc: heading changed since the contents were built: " + ", ".join(stale)); sys.exit(1)
print("golo-toc: %d sections, contents and page agree" % len(toc))
