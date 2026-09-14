#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import David's Google My Map into the archive, whole, before it is switched off.

A My Map dies with the account and no crawler saves one. This takes the KML
export and keeps every part of it: the pins and their notes, the lines, and the
area plots that mark the known lines — which the earlier JSON export dropped.

    curl -sL "https://www.google.com/maps/d/kml?mid=<MID>&forcekml=1" -o mymap.kml
    python3 scripts/import-mymap.py mymap.kml
"""
import sys, io, os, json, re
import xml.etree.ElementTree as ET

NS = {"k": "http://www.opengis.net/kml/2.2"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "site", "src", "data", "mymap.json")

def txt(el, path):
    x = el.find(path, NS)
    return (x.text or "").strip() if x is not None and x.text else ""

def coords(el, path):
    x = el.find(path, NS)
    if x is None or not x.text: return []
    out = []
    for tok in x.text.split():
        p = tok.split(",")
        if len(p) >= 2:
            try: out.append([round(float(p[1]), 6), round(float(p[0]), 6)])   # lat, lon
            except ValueError: pass
    return out

def clean(html):
    """Notes are HTML. Keep the words and pull the links out separately."""
    links = re.findall(r'https?://[^\s<>"\']+', html)
    t = re.sub(r"<br\s*/?>", "\n", html)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"https?://[^\s]+", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{2,}", "\n", t).strip(), list(dict.fromkeys(links))

def run(path):
    root = ET.parse(path).getroot()
    layers = []
    for folder in root.iter("{http://www.opengis.net/kml/2.2}Folder"):
        name = txt(folder, "k:name") or "Untitled layer"
        pins, lines, areas = [], [], []
        for pm in folder.findall("k:Placemark", NS):
            nm = txt(pm, "k:name")
            note, links = clean(txt(pm, "k:description"))
            pt   = coords(pm, ".//k:Point/k:coordinates")
            ls   = coords(pm, ".//k:LineString/k:coordinates")
            poly = coords(pm, ".//k:Polygon//k:outerBoundaryIs//k:LinearRing/k:coordinates")
            rec = {"n": nm}
            if note:  rec["note"]  = note
            if links: rec["links"] = links
            if poly:    areas.append({**rec, "ring": poly})
            elif ls:    lines.append({**rec, "path": ls})
            elif pt:    pins.append({**rec, "c": pt[0]})
        layers.append({"name": name, "pins": pins, "lines": lines, "areas": areas})
    d = {
      "note": ("Imported whole from David's Google My Map on 14 September 2026, before the map is switched off. "
               "A My Map dies with the account and no crawler saves one; this is the copy that survives."),
      "source": "https://www.google.com/maps/d/u/0/edit?mid=1NSF2idD4Q8mN0VQGpBwWPgoJp6Ba1sk",
      "layers": layers,
      "counts": {"layers": len(layers),
                 "pins":  sum(len(l["pins"])  for l in layers),
                 "lines": sum(len(l["lines"]) for l in layers),
                 "areas": sum(len(l["areas"]) for l in layers),
                 "notes": sum(1 for l in layers for p in l["pins"] + l["lines"] + l["areas"] if p.get("note")),
                 "links": sum(len(p.get("links", [])) for l in layers for p in l["pins"] + l["lines"] + l["areas"])},
    }
    json.dump(d, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(d["counts"], indent=1))
    for l in layers:
        print(f"   {len(l['pins']):5d} pins  {len(l['lines']):3d} lines  {len(l['areas']):2d} areas   {l['name']}")

run(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mymap.kml")
