#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fold the FamilySearch IMAGE readings (the viewer's Names panel, read 16 Nov 2026) into the roster rows whose tree citation is a 3:1 image ark.
The text per ark was written by hand from what each image's own name index listed (or did not list); nothing here is taken from a page image.
    python3 scripts/fold-fs-images.py <links.json> [--write]
"""
import json, re, sys
ROSTER = "site/src/data/roster.json"
MARK = re.compile(r"\*\*Not yet read here:\*\*[^*]*?until it is\.")
T = {
 "3:1:3Q9M-CS8K-JQ6R-C": "the viewer opens «Laives. Baptism Records 1605–1907», image 698 of 1,134; its name index lists «Barbara Defranzeschi» with parents «Andreas Defranzeschi» and «Maria Gotardi» (the index spells it Defranzeschi)",
 "3:1:3Q9M-CS8K-JQVZ-8": "the viewer opens «Laives. Baptism Records 1605–1907», image 1090 of 1,134; its name index lists «N Defranceschi» (a baby with no given name) with parents «Franz» and «Vicktoria Dinz»",
 "3:1:939V-5BSG-9": "the viewer opens a New York passenger list of 10–24 April 1882, image 291 of 1,066; its name index lists «Giov de Franceschi», «Angiola de Franceschi», «Romeo de Franceschi», «Marietta de Franceschi» and «Therese de Franceschi» one after another (one party on the manifest, inf)",
 "3:1:33S7-916B-BW7": "the viewer opens «Passenger and crew lists: New York City. Immigration Records Feb 3, 1905», image 63 of 504; its name index lists «Domenico De Franceschi» with a second name «Bartolo De Francesco» beside his",
 "3:1:3Q9M-C9PT-NLLC": "the viewer opens «Passenger and crew lists: New York City. Immigration Records Dec 8, 1905», image 426 of 749; its name index lists «Stefano De Franceschi» with a second name «Gius De Franceschi» beside his",
 "3:1:3QS7-L99F-Q4B5": "the viewer opens «Pola. Death Records July 1797–April 1858», item 5 of the film, image 61 of 147; its name index lists «Mattio de Franceschi» with no parent or spouse named",
 "3:1:939V-5NS6-DH": "the viewer opens a Latin baptism page of a Croatian church book, image 113 of 233 (the viewer shows no volume title, so the book is not identified from this page); its name index lists «Joannem Anto De Franceschi», father «Joanni Antonii De Franceschi», mother «Lutia»",
 "3:1:3QS7-L99X-R3V9": "the viewer opens a Latin baptism page of a Croatian church book, image 87 of 266 (no volume title shown); **its name index lists six babies and their parents (Raderić, Peričić, Kraišković, Kabalin, Ježić, Ferković) and no De Franceschi at all, so this citation does not show the name on the page's index: the image is mis-cited or the entry is unindexed**",
 "3:1:3QS7-899F-Q63": "the viewer opens «Poreč. Religious Death Records 1838–1887», item 2 of the film, image 153 of 212; its name index lists «Elisabetta Defranceschi» with no parent or spouse named, and «Matteo Defranceschi» with «Paolo Percesino» and «Angela Percesino» beside him",
 "3:1:3Q9M-CS87-QQ62-K": "the viewer opens «Nascimentos: Ribeirão Preto. Birth Records January–February 1934», image of 203, and shows «Image Restricted» for this account, so it is not read",
 "3:1:3Q9M-CS7V-FSDG-4": "the viewer opens «Fundo SEADE – Óbitos: São Paulo. Medical Death Certificates November 1995», image of 275, with «No Names» on its index, so nothing is read",
}
ALM_B = "the viewer opens «Almissa. Birth Records Nov 12, 1825–Dec 27, 1850» (DGS film 005494288, item 2 of 118 images, the Almissa = Omiš register); the image has no name index («No Names»), so the tree's claim is not tested and the page image is not opened"
ALM_M = "the viewer opens «Almissa. Marriage Records Dec 27, 1825–Dec 12, 1857» (DGS film 005494288, item 3 of 49 images, the Almissa = Omiš register); the image has no name index («No Names»), so the tree's claim is not tested and the page image is not opened"
for a in ("3:1:3QS7-899X-LNLT","3:1:3QS7-L99X-LFYS","3:1:3QS7-L99X-LF2J","3:1:3QSQ-G99X-LJWG","3:1:3QSQ-G99X-LJ3B","3:1:3QSQ-G99X-LNR1","3:1:3QS7-L99X-LFN9","3:1:3QSQ-G99X-LNGS","3:1:3QSQ-G99X-LNY1"): T[a] = ALM_B
T["3:1:3QS7-L99X-LF4D"] = ALM_M
roster = json.load(open(ROSTER, encoding="utf-8")); rows = {r["pid"]: r for r in roster["rows"]}
links = json.load(open(sys.argv[1], encoding="utf-8"))
per = {}
for pid, name, ark in links: per.setdefault(pid, []).append(ark)
n = 0
for pid, arks in per.items():
    r = rows[pid]
    if not MARK.search(r["note"]): continue
    ims = [a for a in arks if a.startswith("3:1")]
    if not ims or len(ims) != len(arks): continue
    txt = "; ".join(T[a] for a in ims)
    new = "**Read on FamilySearch, 16 November 2026 (the image's name index in the viewer; the page image was not opened):** " + txt + ". Nothing here dates or places the person: name, years and place stay the tree's word (lore) until the page is read."
    r["note"] = MARK.sub(lambda m: new, r["note"], 1); n += 1
print(n, "rows")
if "--write" in sys.argv:
    json.dump(roster, open(ROSTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(ROSTER, "a").write("\n"); print("written")
