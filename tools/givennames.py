#!/usr/bin/env python3
"""Publish the whole given-name canon, sorted into the languages that produced it.

The reconciliation table lives in households.py, where it does the actual work
of merging households. This turns that table into something a reader can use:
every form the archive has met, filed under the language whose clerks wrote it.
"""
import importlib.util, json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hh", os.path.join(ROOT, "tools", "households.py"))
hh = importlib.util.module_from_spec(spec); spec.loader.exec_module(hh)
CANON = hh.CANON

# Which language a given form belongs to. Explicit lists beat endings, because
# Nikolaus is German and Nicolaus is Latin and they differ by one letter.
GERMAN = set("""johann johannes hans josef sepp jakob franz anton nikolaus stefan steffan matthias
 paul peter andreas markus lukas simon vinzenz lorenz martin michael gregor georg thomas
 bartholomaeus christoph klemens augustin sebastian leonhard philipp elisabeth katharina
 helene magdalena margarethe ursula luzia agathe alois aloisia karolina karoline rosa
 theresia therese wilhelm heinrich rudolf ludwig franziska juditha juliana anna maria
 barbara veronica dominik valentin klement""".split())

ENGLISH = set("""john joseph joe james jacob francis frank anthony antony nicholas stephen steve
 matthew paul peter andrew mark luke simon vincent lawrence laurence martin michael mike
 gregory george thomas tom bartholomew christopher clement augustine sebastian leonard
 philip elizabeth catherine katherine helen magdalen margaret ursula lucy agatha mary
 louis lewis charles william henry rudolph nicholas ann anne rose theresa teresa
 dennis alfred robert""".split())

VENETIAN = set("""zuane zuanne zuan zan zanne zorzi piero nane bepi checo toni beto momolo titta
 nani nina bortolo menego anto meneghin gigi bastian polo tita""".split())

CROATIAN = set("""ivan ivo ive josip jozo joso jakov frane franjo ante antun nikola mikula stjepan
 stipe stipan matij matija mate mato pavao pave petar pere andrija andro marko luka sime
 vinko lovre martin mihovil grgur jure juraj tomo tome bartol krsto kliment katarina jelena
 magdalena marija mara ana ursula ursa lucija agata jelka kata dragica ruza ruzica zdravko
 krstitelj nada stefan mihovel nikolina antonija franciska""".split())

LATIN_END = re.compile(r"(us|um|ae|æ|orum|ÿ|is)$")
LATIN_EXTRA = set("""joannem joanni joannis gioannis ioannis mathæi antonii francisci josephi
 nicolai stephani valentini aloysii dominici pauli petri andreæ jacobi blasii thomæ lucæ marci
 simonis vincentii laurentii martini michaelis gregorii bartholomæi christophori clementis
 augustini sebastiani leonardi philippi elisabethæ catharinæ helenæ magdalenæ margaritæ
 ursulæ luciæ agathæ mariæ antoniæ franciscæ
 joannes gioannes ioannes mathias mathia matthias nicolaus stephanus valentinus dominicus
 hieronymus vincentius laurentius bartholomaeus christophorus augustinus sebastianus
 leonardus philippus elisabetha catharina magdalena margarita agatha helena""".split())

def fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def classify(form):
    f = form.lower(); g = fold(f)
    if f in GERMAN or g in GERMAN:      return "german"
    if f in ENGLISH or g in ENGLISH:    return "english"
    if f in VENETIAN or g in VENETIAN:  return "venetian"
    if f in CROATIAN or g in CROATIAN:  return "croatian"
    if f in LATIN_EXTRA or LATIN_END.search(f): return "latin"
    return "italian"

def cap(s):
    return s[:1].upper() + s[1:]

rows = []
for canon, blob in CANON.items():
    forms = [f for f in dict.fromkeys(blob.split()) if f]
    buckets = {k: [] for k in ("latin", "italian", "venetian", "croatian", "german", "english")}
    for f in forms:
        buckets[classify(f)].append(cap(f))
    # the canonical form itself always belongs to Italian
    if cap(canon) not in buckets["italian"]:
        buckets["italian"].insert(0, cap(canon))
    row = {"canon": canon, "forms": len(forms)}
    for k, v in buckets.items():
        # keep it readable: at most six per language, longest-first is unhelpful, so keep register order
        row[k] = ", ".join(v[:6]) if v else "—"
    rows.append(row)

rows.sort(key=lambda r: -r["forms"])
out = {"rows": rows,
       "note": "Reconciled by hand from the forms that actually occur in these registers.",
       "totalForms": sum(r["forms"] for r in rows)}
json.dump(out, open(os.path.join(ROOT, "site", "src", "data", "givennames.json"), "w"),
          indent=1, ensure_ascii=False)
print(f"{len(rows)} names, {out['totalForms']} forms")
for r in rows[:6]:
    print(f"  {r['canon']:12s} L:{r['latin'][:34]:36s} HR:{r['croatian'][:26]}")
