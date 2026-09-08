#!/usr/bin/env python3
"""Pull public-domain and openly licensed images from Wikimedia Commons.

Every image keeps its Commons page, its licence and its author, because a
picture without those is a picture this archive cannot honestly publish.
Writes optimised WebP into site/public/art/ and appends to art-src.json.
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "site", "public", "art")
MAN  = os.path.join(ROOT, "site", "src", "data", "art-src.json")
UA   = {"User-Agent": "DefranceschiArchive/1.0 (family history research; contact david.defranceski@gmail.com)"}

WANT = [
 ("carlo-portrait",   "File:CarloDeFranceschi.jpg"),
 ("palladio-1570",    "File:Andrea palladio, i quattro libri dell'architettura, per domenico de' franceschi, venezia 1570 (mo, bibl civica).jpg"),
 ("domenico-goleta",  "File:Domenico dei Franceschi, Karl V's erobring af fæstningen Goleta nær Tunis, , KKSgb6434-2, Statens Museum for Kunst.jpg"),
 ("delonne-portrait", "File:Jean-Baptiste Franceschi-Delonne par Vayron.jpg"),
 ("delonne-capture",  "File:Capture du général Franceschi-Delonne le 28 juin 1809.jpg"),
 ("defrance-portrait","File:DeFrance.jpg"),
 ("andrea-nga",       "File:After Titian, Andrea de' Franceschi, late 16th or early 17th century, NGA 42.jpg"),
]

def api(titles):
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
         "&prop=imageinfo&iiprop=url|size|extmetadata&titles=" +
         urllib.parse.quote("|".join(titles)))
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90))

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()

def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        sys.stderr.write(" ".join(cmd[:3]) + " FAILED: " + r.stderr.decode()[:160] + "\n")
    return r.returncode == 0

def main():
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MAN, encoding="utf-8")) if os.path.exists(MAN) else []
    have = {a["id"] for a in man}
    data = api([t for _, t in WANT])
    by_title = {p["title"]: p for p in data["query"]["pages"].values()}
    for pid, title in WANT:
        if pid in have:
            print("have", pid); continue
        p = by_title.get(title)
        if not p or "imageinfo" not in p:
            print("MISSING", title); continue
        ii = p["imageinfo"][0]; em = ii.get("extmetadata", {})
        g  = lambda k: clean((em.get(k) or {}).get("value", ""))
        raw = os.path.join(OUT, pid + ".src")
        try:
            urllib.request.urlretrieve(
                urllib.request.Request(ii["url"], headers=UA).full_url, raw) if False else None
            req = urllib.request.Request(ii["url"], headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r, open(raw, "wb") as f:
                f.write(r.read())
        except Exception as e:
            print("DOWNLOAD FAILED", pid, e); continue
        full  = os.path.join(OUT, pid + ".webp")
        thumb = os.path.join(OUT, pid + "-t.webp")
        ok  = run(["magick", raw, "-auto-orient", "-resize", "1600x1600>", "-quality", "82", full])
        ok &= run(["magick", raw, "-auto-orient", "-resize", "620x620>",   "-quality", "78", thumb])
        os.remove(raw)
        if not ok: continue
        man.append({
            "id": pid, "file": title,
            "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "licence": g("LicenseShortName") or "Public domain",
            "artist": g("Artist"), "date": g("DateTimeOriginal"),
            "credit": g("Credit"), "desc": g("ImageDescription"),
            "w": ii.get("width"), "h": ii.get("height"),
            "src": "/art/%s.webp" % pid, "thumb": "/art/%s-t.webp" % pid,
        })
        print("ok", pid, ii.get("width"), "x", ii.get("height"), "|", g("LicenseShortName"))
    json.dump(man, open(MAN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(man), "images ->", MAN)

if __name__ == "__main__":
    main()
