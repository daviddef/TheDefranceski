#!/usr/bin/env python3
"""Turn «DGS 005497826, frame 627» into a link to that image on FamilySearch.

The Pomer entries cite film and frame as text; this makes each one clickable so a reader
can open the exact page. DGS 005497826 is the births volume (frame = 621 + image number,
waypoint 9R2F-FMH); DGS 005497827 holds the marriages (frames 1-44, waypoint 9R2F-ZNT) and
the deaths (frames 45-101, 9R2F-6YM, image number = frame - 44).

A frame is linked only when it falls inside the volume it is cited under, and never twice.
Idempotent: a number already inside a markdown link is left alone.
    scripts/link-pomer-frames.py           # report
    scripts/link-pomer-frames.py --write
"""
import json, io, re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARKS = os.environ.get("POMER_ARKS", "")
A = json.load(open(ARKS)) if ARKS and os.path.exists(ARKS) else None
if A is None:
    A = json.load(open(os.path.join(ROOT, "data/pomer-arks.json")))

def target(dgs, frame):
    if dgs == "005497826":
        idx, vol = frame - 621, "births"
        ok = 1 <= idx <= 86
    else:
        if frame <= 44: idx, vol, ok = frame, "marriages", frame >= 1
        else: idx, vol, ok = frame - 44, "deaths", 1 <= frame - 44 <= 57
    if not ok: return None
    return f"https://www.familysearch.org/ark:/61903/{A[vol]['arks'][idx-1]}?cc=2040054&wc={A[vol]['wp'].split(':')[0]}"

DGS = re.compile(r"DGS (005497826|005497827)")
FR = re.compile(r"\b(frames?) (\d{1,3}(?:(?:, | and )\d{1,3})*)")

def link(text):
    if not text or "DGS 0054978" not in text: return text, 0
    marks = [(m.start(), m.group(1)) for m in DGS.finditer(text)]
    out, last, n = [], 0, 0
    for m in FR.finditer(text):
        prev = [d for p, d in marks if p < m.start()]
        # the nearest DGS before the frame, within 160 characters, else not ours to guess
        near = [(p, d) for p, d in marks if 0 < m.start() - p < 160]
        if not near: continue
        dgs = near[-1][1]
        if text[max(0, m.start() - 1):m.start()] == "[": continue
        if re.search(r"\]\([^)]*$", text[:m.start()]) : continue
        # birth/death/marriage secondary notation «births frame 6» sits after a DGS frame: skip words before 'frame'
        pre = text[max(0, m.start() - 8):m.start()]
        if re.search(r"(births|deaths|marriages) $", pre): continue
        nums = re.split(r", | and ", m.group(2))
        parts, pos = [], m.start(2)
        body = m.group(2)
        rebuilt, cur = "", 0
        changed = False
        for mm in re.finditer(r"\d{1,3}", body):
            u = target(dgs, int(mm.group(0)))
            rebuilt += body[cur:mm.start()]
            rebuilt += f"[{mm.group(0)}]({u})" if u else mm.group(0)
            changed |= bool(u); cur = mm.end()
        rebuilt += body[cur:]
        if changed:
            out.append(text[last:m.start(2)]); out.append(rebuilt); last = m.end(2); n += 1
    out.append(text[last:])
    return "".join(out), n

def main():
    write = "--write" in sys.argv
    tot = 0
    L = os.path.join(ROOT, "site/src/data/liznjan.json")
    l = json.load(io.open(L, encoding="utf-8"))
    for key in ("lead", "source_p"):
        l["pomer"][key], k = link(l["pomer"].get(key, ""))
        tot += k
    for r in l["pomer"]["rows"]:
        r["text"], k = link(r["text"]); tot += k
    R = os.path.join(ROOT, "site/src/data/roster.json")
    ro = json.load(io.open(R, encoding="utf-8"))
    for x in ro["rows"]:
        if "DGS 0054978" in (x.get("note") or ""):
            x["note"], k = link(x["note"]); tot += k
    print(f"link-pomer-frames: {tot} citation(s) linked" + ("" if write else " (report only)"))
    if write:
        io.open(L, "w", encoding="utf-8").write(json.dumps(l, indent=2, ensure_ascii=False))
        io.open(R, "w", encoding="utf-8").write(json.dumps(ro, indent=1, ensure_ascii=False))
main()
