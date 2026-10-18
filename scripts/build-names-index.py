#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the two files the kit's build-time name linker reads (kit/tools/autolink.py, kit/docs/autolink.md).

    python3 scripts/build-names-index.py             write private/autolink/names-index.json and living.json
    python3 scripts/build-names-index.py --print     print the counts, write nothing

THE HISTORY (18 October 2026). The names used to be linked in the reader's browser: site/public/wholink.js fetched
site/public/whoindex.json and wrapped the first three mentions of each name per page. Without JavaScript, and for a
crawler, nothing was linked; the file was a September snapshot nobody regenerated (631 names, 175 of them page titles).
scripts/build-whoindex.py (the first form of this file) rebuilt it from the roster, and that generator's RESOLUTION
RULES are kept here, tightened (see «deceased», below). The browser linker and its list are retired: the kit now
links the FIRST mention of a person in each section of the BUILT html, once, after the build, and a gate
(checklinks.py, ratchet .linkfloor.json) stops the number of unlinked names rising.

WHAT IS WRITTEN, and where. Both files go to private/autolink/, which is gitignored (private/ is):

  names-index.json   {"people": [{"name", "aliases", "url"}], "ambiguous": [{"name", "aliases", "url"}]}
  living.json        the names, spellings and addresses of every person the archive does not KNOW to be dead

THE RESOLUTION RULES. Everything is read from the COMMITTED roster (site/src/data/roster.json) and dossiers; nothing
private is needed, so a CI runner, which has no tree, builds exactly the same two files as David's machine (the tree
only ADDS names to living.json when it is there; see below).

  * A name is a roster name with a bracketed nickname or maiden name dropped (build-dossiers.py's needle), two words
    or more, no digits, beginning with a capital, not a placeholder («Unknown ...», «... Others ...»).
  * Rows are grouped by the name's slug (case, accents, punctuation folded). The people behind a name are the
    CANONICAL person of each row (a row `sameAs` another is the same person, read twice and spelled differently).
  * UNIQUE: exactly one person bears the name, and that person is DECEASED and has a page. The entry's url is
    /person/<pid>/ of the canonical row, the page the name page itself names as canonical for a sole bearer. Every
    other spelling the roster holds for that SAME person (the sameAs duplicate, an accent variant) is an alias.
  * AMBIGUOUS: two or more people bear the name, EVERY one of them deceased with a page. The url is the name page
    the roster rows carry (`who`), which lists each of them. A name with ANY bearer who is not known to be dead is
    left out altogether (the kit: «link such a name to the disambiguation address or not at all»).
  * DECEASED means the roster shows it, and a presumption is not enough. Count as dead: a death year, the
    `deceased` mark, a burial or headstone source, a birth year of 1900 or earlier (or an estimated one), or NO
    dates at all but a source that reads an old register (read, household, golo, chart, namesake, life). Everything
    else is «not known to be dead» and so never linked: a living row, a row the living rule calls living, a person
    born after 1900 with no death recorded (the rule treats a public record as «not living» but a register entry of
    1953 does not make a man dead), and an undated person from the family tree or a modern record. The first form of
    this generator listed 44 people born after 1900 with no death, one born in 1953; this one lists none.

living.json is the safety net, built from the SAME decision: every person NOT known to be dead (all their spellings
and their /person/ and /who/ addresses). The kit stops (exit 2) if the index holds any of it, and refuses to link a
dead name that overlaps one of those names in a sentence. When David's tree is on the machine (living_v2.gedcom_path)
the living and held-out people of the tree are added too; in CI there is no tree and the file is the committed
decision alone, which is also all the index is made from. The worth of the tree is a CHECK, not a filter: if the
tree names a living or held-out person whose name is also an index entry, the kit refuses and the build stops.

check-names-index.py reads the files against the roster by independent code and plants faults to prove it.
"""
import os, re, sys, json, unicodedata, importlib.util
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")
OUTDIR = os.path.join(ROOT, "private", "autolink")
NAMESAKES = os.path.join(ROOT, "data", "autolink-namesakes.json")

# An undated row is taken as dead only when its source reads an OLD register or is the archive's own historical
# apparatus. «myheritage» (the family tree), «record» (an index that includes modern entries), «oesta», «press»,
# «paper», «gazette», «line», «eleven» can name someone alive or someone whose death nobody recorded.
UNDATED_DEAD_SRC = ("read", "household", "golo", "chart", "namesake", "life")
OLDEST_BIRTH = 1900
SEARCH = "/search/?q="                           # the archive's own search (kit Search.astro reads ?q=)
PLACEHOLDER = re.compile(r"\b(unknown|unnamed|others|anonymous|illegible|n\.?n\.?)\b", re.I)


def slugify(s):
    """The same function as build-dossiers.py, so a slug here is the slug of the /who/ page."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def base_name(name):
    """A roster name as it would be written in running prose: «(Bortolussi)» and «(Petar)» dropped."""
    return " ".join(re.sub(r"\s*\(.*?\)\s*", " ", str(name or "")).split())


def is_name(s):
    """Two words or more, no digits, begins with a capital letter, and is not a placeholder."""
    if len(s) < 5 or len(s.split()) < 2 or re.search(r"\d", s) or PLACEHOLDER.search(s):
        return False
    return bool(re.match(r"^[^\W\d_]", s)) and s[0].isupper()


def _living_v2():
    spec = importlib.util.spec_from_file_location("living_v2", os.path.join(HERE, "living_v2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def known_dead(row):
    """True when the roster ITSELF shows the person is dead (not merely that the living rule lets them be shown)."""
    if row.get("living"):
        return False
    if row.get("d") or row.get("deceased") or row.get("src") in ("burial", "grave"):
        return True
    b = row.get("b") or row.get("bEst")
    if b:
        return int(b) <= OLDEST_BIRTH
    return row.get("src") in UNDATED_DEAD_SRC


def canonical_ids(rows):
    """pid -> pid of the person it is (a row `sameAs` another is that other, followed to the end of a chain)."""
    pids = {r["pid"] for r in rows if r.get("pid")}
    to = {r["pid"]: r.get("sameAs") for r in rows if r.get("pid")}
    out = {}
    for p in pids:
        seen, cur = set(), p
        while to.get(cur) and to[cur] in pids and cur not in seen:
            seen.add(cur)
            cur = to[cur]
        out[p] = cur
    return out


def person_groups(rows):
    """canonical pid -> [every roster row that is this person]."""
    canon = canonical_ids(rows)
    g = {}
    for r in rows:
        if r.get("pid"):
            g.setdefault(canon[r["pid"]], []).append(r)
    return g, canon


def group_status(group, L2=None):
    """A person (all the rows that are them): «living» if any row is marked living or the living rule calls it
    living; «dead» if the roster shows a death and no row is living; otherwise «unsure» (not living by the rule,
    not shown to be dead: a man born in 1953 with a record and no death, an undated person from the family tree)."""
    for r in group:
        if r.get("living") or (L2 is not None and L2.row_is_living(r)):
            return "living"
    return "dead" if any(known_dead(r) for r in group) else "unsure"


_DESCRIPTOR = re.compile(r"\s*(?:,|«|\bq\.|\bnée\b|\bdetto\b|\bdetti\b|\bcalled\b|\bthe\b|\bof\b)")
_NICK = re.compile(r"\s*[“\"«][^”\"»]*[”\"»]\s*")


def case_forms(spellings):
    """Spellings the kit would treat as one name (it folds case) reduced to one, the form the prose uses. The kit
    keeps the FIRST of two spellings that differ only in case and matches it exactly, so the form must be right;
    the roster's «DeFranceschi» (a tree import's camel case) never appears in the running text, «Defranceschi»
    does. The order of the rest is kept."""
    out, seen = [], set()
    for s_ in spellings:
        s_ = s_.replace("DeFranceschi", "Defranceschi").replace("DeFranceski", "Defranceski")
        if s_.casefold() not in seen:
            seen.add(s_.casefold())
            out.append(s_)
    return out


def pool_names(name):
    """[(pool key, spelling, usable)] a roster name stands for. A label the roster wrote for itself («Maria
    Defranceschi, daughter of Antonio», «Luigi "Louis" Defranceschi», «Giovanni / Gian Battista Defranceschi»)
    is a bearer of the plain name or names inside it, so it counts against that name being one person's.
    Only the plain head of a label (the name before a comma, a «née», a nickname) is a spelling that may be
    LINKED (usable); the alternatives of a slash label are read by guessing which words are alternatives, so
    they are counted as bearers and never linked. Spellings that differ only in «de Franceschi» /
    «Defranceschi» share a key (the archive's own resolver, lib/people.js, holds them equal): a unique name is
    unique in either spelling."""
    nm = base_name(name)
    parts = [x.strip() for x in nm.split(" / ")]
    slash = len(parts) > 1
    if slash:
        tail = parts[-1].split(" ", 1)[1] if " " in parts[-1] else ""
        alts = [(x + " " + tail).strip() for x in parts[:-1]] + [parts[-1]]
    else:
        alts = [nm]
    out = []
    for alt in alts:
        alt = _NICK.sub(" ", alt)
        m = _DESCRIPTOR.search(alt)
        if m:
            alt = alt[:m.start()]
        alt = " ".join(alt.split())
        k = slugify(alt).replace("de-franceschi", "defranceschi")
        if k and not any(o[0] == k and o[1] == alt for o in out):
            out.append((k, alt, not slash))
    return out


# Forenames a register writes in every language, which no surname here is. A name that ENDS in one is two forenames.
FORENAMES = frozenset("""maria mariae mariam marie anna annae annam joannes johannes joannem ioannes giovanni joannis
 johann johannis josephus joseph josephum giuseppe josephi franciscus francesco franciscum francisci petrus petri pietro
 paulus paolo antonius antonio antonii antonium baptista battista batta bapt jacobus giacomo iacobus nicolaus nicolo
 matthaeus matheus mattheus matteo georgius giorgio gregorius carolus carlo ludovicus luigi aloysius aloisius
 catharina caterina cattarina theresia teresa elisabetha elisabetta margaretha margherita sebastianus dominicus
 domenico vincentius vincenzo stephanus stefano laurentius lorenzo martinus martino bartholomaeus bortolo
 andreas andrea thomas tomaso michael michele leonardus leonardo ambrosius ambrogio angelus angelo""".split())
_SURNAME_FIRST =("de franceschi ", "defranceschi ", "franceschi ", "de' franceschi ")


def given_name_counts(rows, canon):
    """slug of a word -> (number of people whose name BEGINS with it, number whose name ENDS with it)."""
    first, last = {}, {}
    for r in rows:
        w = base_name(r.get("name")).split()
        if len(w) >= 2:
            pid = canon.get(r.get("pid")) or r.get("name")
            first.setdefault(slugify(w[0]), set()).add(pid)
            last.setdefault(slugify(w[-1]), set()).add(pid)
    return {k: len(v) for k, v in first.items()}, {k: len(v) for k, v in last.items()}


def ends_in_given_name(name, first, last):
    """True for «Anna Maria», «Antonius Matheus»: a name whose last word is far likelier a forename than a surname
    (more names begin with it than end with it). A name in register order, surname first («De Franceschi
    Giovanni»), is left alone."""
    if name.lower().startswith(_SURNAME_FIRST):
        return False
    k = slugify(name.split()[-1])
    return k in FORENAMES or (first.get(k, 0) >= 2 and first.get(k, 0) >= last.get(k, 0))


def is_plain(name):
    """A name as the prose would write it: no label, no nickname, no alternative spellings, no bracket."""
    return name == _NICK.sub(" ", name).strip() and " / " not in name and not _DESCRIPTOR.search(name) \
        and is_name(name)


def build(rows, people, L2=None, tree_names=(), namesakes=None):
    """-> (index, living, stats). rows: roster rows. people: dossiers `people` (slug -> {...}); tree_names: extra
    living or held-out names from David's tree (empty in CI)."""
    groups, canon = person_groups(rows)
    status = {p: group_status(g, L2) for p, g in groups.items()}
    first, last = given_name_counts(rows, canon)
    # pool key -> {canonical pid: [(row, spelling)]}
    bearers_of = {}
    for r in rows:
        pid = canon.get(r.get("pid")) or ("anon:" + base_name(r.get("name")))
        for key, sp, usable in pool_names(r.get("name")):
            bearers_of.setdefault(key, {}).setdefault(pid, []).append((r, sp, usable))

    who_persons = {}                                    # name page -> the people it lists
    for r in rows:
        if r.get("who") and r.get("pid"):
            who_persons.setdefault(r["who"], set()).add(canon.get(r["pid"]))
    people_by_pid, ambiguous = {}, []
    for key, bearers in bearers_of.items():
        st = [status.get(p) for p in bearers]           # None: a row with no pid, so no page
        if any(x in (None, "living") for x in st):
            continue                                   # a living bearer, or one with no page: never linked
        if len(bearers) == 1:
            (pid,) = bearers
            if status[pid] != "dead":
                continue                               # one person not shown to be dead: not linked as a person
            # an alias must come from the person's OWN row (an alternative spelling inside its label) or be the
            # same name in the other orthography; a duplicate row that reads a different name is not an alias
            own_keys = {k for k, _s, _u in pool_names(next(r for r in groups[pid] if r["pid"] == pid)["name"])}
            if key not in own_keys:
                continue
            sp = []
            for r, s_, usable in bearers[pid]:
                if usable and is_name(s_) and s_ not in sp and not ends_in_given_name(s_, first, last):
                    sp.append(s_)
            sp = case_forms(sp)
            if sp:
                people_by_pid.setdefault(pid, []).append((key, sp))
            continue
        # SEVERAL people bear the name (in either orthography). Each exact spelling the roster writes plainly gets
        # an entry: to ITS name page /who/<slug>/ when that page really lists two or more people and no living
        # one, and otherwise to the archive's search for the name, which finds every mention.
        by_spelling = {}
        for rs in bearers.values():
            for r, s_, _u in rs:
                if s_ == base_name(r["name"]) and is_plain(s_) and not ends_in_given_name(s_, first, last):
                    by_spelling.setdefault(slugify(s_), set()).add(s_)
        for sk, spell in by_spelling.items():
            sps = case_forms(sorted(spell, key=lambda x: (x.count("DeFranceschi"), x)))
            who = "/who/%s/" % sk
            if sk in people and who in who_persons and len(who_persons[who]) >= 2 \
                    and not any(status.get(p_) in (None, "living") for p_ in who_persons[who]):
                url = who
            else:
                url = SEARCH + quote(sps[0], safe="")
            ambiguous.append({"name": sps[0], "aliases": sps[1:], "url": url})

    out_people = []
    for pid, forms in people_by_pid.items():
        names = []
        for _k, sp in sorted(forms):
            for s_ in sp:
                if s_ not in names:
                    names.append(s_)
        own = case_forms([base_name(next(r for r in groups[pid] if r["pid"] == pid)["name"])])[0]
        if own in names:                                # the person's own row names the entry
            names.remove(own)
            names.insert(0, own)
        out_people.append({"name": names[0], "aliases": names[1:], "url": "/person/%s/" % pid})
    # dead people whose name a living or held-out person of David's tree ALSO bears (found on his machine, where the
    # tree is, and recorded in data/autolink-namesakes.json so that a runner without the tree leaves them out too)
    ns = namesakes or {}
    drop_pids = {"/person/%s/" % p_ for p_ in ns.get("pids", [])}
    drop_names = {" ".join(n_.split()).casefold() for n_ in ns.get("names", [])}
    out_people = [e for e in out_people if e["url"] not in drop_pids]
    ambiguous = [e for e in ambiguous if " ".join(e["name"].split()).casefold() not in drop_names]
    out_people.sort(key=lambda e: (e["name"].casefold(), e["url"]))
    ambiguous.sort(key=lambda e: (e["name"].casefold(), e["url"]))

    # ---- living.json: everyone the roster does not show to be dead
    names, urls = set(), set()
    not_dead = [p for p in groups if status[p] != "dead"]
    listed = {s.casefold() for e in out_people + ambiguous for s in [e["name"]] + e["aliases"]}
    for p in not_dead:
        for r in groups[p]:
            for n in (r.get("name"), base_name(r.get("name"))):
                n = " ".join(str(n or "").split())
                # a name an AMBIGUOUS entry sends to the name page is shared with a person not known to be dead
                # on purpose; the other names of such people stay on the list
                if len(n.split()) >= 2 and not (status[p] == "unsure" and n.casefold() in listed):
                    names.add(n)
            urls.add("/person/%s/" % r["pid"])
    who_bearers = {}
    for r in rows:
        if r.get("who"):
            who_bearers.setdefault(r["who"], []).append(status.get(canon.get(r.get("pid"))))
    amb_urls = {e["url"] for e in ambiguous}
    for w, sts in who_bearers.items():
        if w not in amb_urls and all(x != "dead" for x in sts):   # a name page nobody shown dead stands on
            urls.add(w)
    for n in tree_names:
        if n and len(n.split()) >= 2:
            names.add(" ".join(n.split()))
    living = {"names": sorted(names), "urls": sorted(urls)}
    stats = {"rows": len(rows), "people": len(out_people), "aliases": sum(len(e["aliases"]) for e in out_people),
             "ambiguous": len(ambiguous), "not_known_dead": len(not_dead), "living_names": len(names),
             "living_urls": len(urls), "tree_names": len(tree_names)}
    return {"people": out_people, "ambiguous": ambiguous}, living, stats


def load(data=DATA):
    with open(os.path.join(data, "roster.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    with open(os.path.join(data, "dossiers.json"), encoding="utf-8") as f:
        people = json.load(f)["people"]
    return rows, people


def tree_living_names(L2):
    """The living and held-out people of David's tree, when it is on this machine. -> (names, found)."""
    path = L2.gedcom_path()
    if not path:
        return [], False
    tree = L2.load_tree(path)
    out = set()
    for uid, p in tree.people.items():
        living, minor = tree.verdict(uid)
        if living or minor:
            out.add(p["name"])
    return sorted(out), True


def load_namesakes(path=NAMESAKES):
    if not os.path.exists(path):
        return {"pids": [], "names": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tree_collisions(index, tree_names):
    """-> (pids, names): index entries (a /person/ entry by its pid, an ambiguous one by its name) that a living or
    held-out person of the tree also bears. The kit compares names folded to case with straight apostrophes."""
    def key(n):
        n = unicodedata.normalize("NFC", n or "")
        for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u02bc", "'"), ("\u00b4", "'"), ("\u2010", "-"), ("\u2011", "-")):
            n = n.replace(a, b)
        return " ".join(n.split()).casefold()
    tk = {key(n) for n in tree_names}
    pids = sorted(e["url"].strip("/").split("/")[-1] for e in index["people"] if any(key(n) in tk for n in [e["name"]] + e["aliases"]))
    names = sorted(e["name"] for e in index["ambiguous"] if any(key(n) in tk for n in [e["name"]] + e["aliases"]))
    return pids, names


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv):
    L2 = _living_v2()
    rows, people = load()
    names, found = ([], False) if "--no-tree" in argv else tree_living_names(L2)
    ns = load_namesakes()
    index, living, stats = build(rows, people, L2, names, ns)
    msg = ("names-index: %(people)d people (%(aliases)d aliases), %(ambiguous)d ambiguous; living.json: "
           "%(not_known_dead)d roster people not shown to be dead, %(living_names)d names, %(living_urls)d addresses" % stats)
    msg += "; tree %s (%d living or held-out names added)" % ("found" if found else "not found, committed data only", len(names))
    if "--print" in argv:
        print(msg)
        return 0
    if found:
        pids, amb = tree_collisions(index, names)
        if pids or amb:
            print(msg)
            print("names-index: REFUSED. %d index entr%s a name a living or held-out person of the tree also bears. "
                  "Add to data/autolink-namesakes.json (a dead person's page id, which names no living person):\n"
                  "  \"pids\": %s\n  \"names\": %s" % (len(pids) + len(amb), "y holds" if len(pids) + len(amb) == 1 else "ies hold",
                                                         json.dumps(pids), json.dumps(amb, ensure_ascii=False)))
            return 2
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "names-index.json"), "w", encoding="utf-8") as f:
        f.write(dumps(index))
    with open(os.path.join(OUTDIR, "living.json"), "w", encoding="utf-8") as f:
        f.write(dumps(living))
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
