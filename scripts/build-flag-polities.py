#!/usr/bin/env python3
"""The flag eras of the Record Atlas, for the countries this archive's people lived in: what the flag was *of*, the pills the Atlas gives it
(the regime, the leader, the religion or ideology, each with its note), the «Who & why» and «What it represents» paragraphs, and the drawing.

A person's page shows, for each place on their route, the era the place was in the year they were there. The slice in
data/tree-page/atlas-data.json holds the drawings and which flag stood over which place from which year, but not any of this text; it lives
in the Atlas's own flag pages (site/src/flags-pages/<country>-flags.html, one `.entry` per era). Reading those pages is reading the Atlas's
own words, not rewriting them. Writes site/src/data/flag-eras.json: {«<slug>--<era id>»: {from,to,dates,polity,caption,vb,svg,pills:[{t,dot,tip}],why,rep}}.

    RECORD_ATLAS="/path/to/Record Atlas" python3 scripts/build-flag-polities.py
"""
import html, json, os, re, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
atlas = os.path.expanduser(os.environ.get("RECORD_ATLAS", "~/Projects/Family Projects/Record Atlas"))
sl = json.load(open(os.path.join(root, "data/tree-page/atlas-data.json"), encoding="utf-8"))
pages = os.path.join(atlas, "site/src/flags-pages")
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")

# which flag pages are needed: every page a flag in the slice is filed on, and the page of each place's own country
need = {fid.partition("--")[0] for fid in sl["fid"]} | {slug(p.get("cn")) + "-flags" for p in sl["places"] if p.get("cn")}

def text(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

out, missing = {}, []
for pg in sorted(need):
    path = os.path.join(pages, pg + ".html")
    if not os.path.exists(path):
        missing.append(pg); continue
    h = open(path, encoding="utf-8").read()
    parts = re.split(r'<div class="entry"[^>]*?\bid="([^"]+)"[^>]*>', h)   # the entries carry other attributes too (data-n=...)
    for eid, chunk in zip(parts[1::2], parts[2::2]):
        m = re.search(r'<svg viewBox="([^"]+)"[^>]*>(.*?)</svg>', chunk, re.S)
        dates = re.search(r'class="card-dates">(.*?)</div>', chunk, re.S)
        title = re.search(r'class="card-title">(.*?)</h3>', chunk, re.S)
        cap = re.search(r'class="flag-caption">(.*?)</div>', chunk, re.S)
        why = re.search(r'<span class="label">Who &amp; why:</span>(.*?)</p>', chunk, re.S)
        rep = re.search(r'<span class="label">What it represents:</span>(.*?)</p>', chunk, re.S)
        tags = []
        for t in re.finditer(r'<span class="tag"([^>]*)><span class="dot" style="background:([^"]+)"></span>(.*?)</span>', chunk, re.S):
            tip = re.search(r'data-tip="([^"]*)"', t.group(1))
            if text(t.group(3)): tags.append({"t": text(t.group(3)), "dot": t.group(2), "tip": html.unescape(tip.group(1)) if tip else ""})
        yrs = re.search(r"era-(\d+)", eid)
        d = text(dates.group(1)) if dates else ""
        rng = re.findall(r"\d{3,4}", d)
        fr = int(rng[0]) if rng else (int(yrs.group(1)) if yrs else None)
        to = int(rng[1]) if len(rng) > 1 else (9999 if re.search(r"present|now", d, re.I) else fr)
        if not (m and title) or fr is None: continue
        out[f"{pg}--{eid}"] = {"from": fr, "to": to, "dates": d, "polity": text(title.group(1)), "caption": text(cap.group(1)) if cap else "",
                               "vb": m.group(1), "svg": m.group(2), "pills": tags, "why": text(why.group(1)) if why else "", "rep": text(rep.group(1)) if rep else ""}
json.dump(out, open(os.path.join(root, "site/src/data/flag-eras.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"{len(out)} flag eras from {len(need) - len(missing)} pages; no page for: {', '.join(missing) or 'none'}")
