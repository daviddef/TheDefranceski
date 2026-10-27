#!/usr/bin/env python3
"""Catch a correction that was published but never propagated.

Why this exists. On 28 September 2026 this archive corrected the mother of a
1743 baptism from «Francisca» to «Pascasia», wrote it up on /corrections/, on
the person's page and on the worklist — and left the wrong name standing in
`households.json`, where it was still the basis of a household, still the basis
of the «two contemporary Jacobos» split, and still the transcription a reader
would meet. The child was filed under the wrong household for five days AFTER
the correction was published.

A correction is not done when it is written. It is done when the old claim is
gone from every file that asserts it. This script is the difference.

How it works: each rule is (label, wrong-pattern, allowed-files). The wrong
pattern is text that should no longer appear as a live claim. Files that are
ALLOWED to contain it are those that quote the error on purpose — the
corrections page, the worklist's own narrative, and the person page that tells
the story of the fix. Anywhere else is a leak.

    python3 scripts/check-propagation.py
"""
import json, os, re, sys

# Resolve from this file, not the cwd: the gate runs its checks from site/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

# (label, regex, files permitted to contain it)
RULES = [
    (u"Maria Defranceschi's mother called «Magdalena Davi\u0107» (every Pomer entry and the Medulin cell read BUI\u0106)",
     # A single-cell misread of a capital this scribe makes two ways, carried for a month as a
     # named person. The correction quotes the old name on purpose; so do the log row that
     # records the old reading and the worklist's own narrative; generated files mirror them.
     # liznjan.json tells the correction in its Pomer section and must name what it corrects.
     r"Magdalena Davi[\u0107c]",
     {"corrections.json", "searched.json", "worklist.json", "dossiers.json", "searchindex.json",
      "liznjan.json"}),
    (u"the Li\u017enjan child of 1870 still called \u00abTusca\u00bb (the register reads FUSCA, twice)",
     # Her pid and her /who/ URL are FROZEN and legitimately keep the old
     # spelling, so the pattern deliberately matches only the NAME form.
     r"Tusca Defranceschi|\"name\": \"Tusca\"|\"n\": \"Tusca\"",
     # Each of these quotes the old spelling inside the sentence that corrects
     # it \u2014 the correction row, the story section, the log row, the worklist
     # item \u2014 and register.json holds the indexed lead under its own id.
     {"corrections.json", "liznjan.json", "searched.json", "worklist.json",
      "register.json", "reconcile.json", "households.json", "explorer.json",
      "dossiers.json", "searchindex.json"}),
    ("Amalia Peschle given as «ex Silesia» (the word reads «ex Volosca»)",
     r"(?:PESCHLE|Peschle|Amalia)[^\"]{0,40}(?:ex SILESIA|ex Silesia|«ex Silesia»)",
     # the corrections page, the worklist item that is withdrawn, the Peschle
     # page, the line page and the log rows all quote the error in the sentence
     # that corrects it; generated files mirror them
     {"corrections.json", "worklist.json", "marriedin.json", "gologorica.json",
      "searched.json", "dossiers.json", "searchindex.json"}),
    ("the Peschle asserted to reach Silesia",
     r"FAMILY REACHES SILESIA|a Peschle out of Silesia",
     {"corrections.json", "dossiers.json", "searchindex.json"}),
    ("Casparus's mother given as Francisca",
     r"Casparus[^\"]{0,140}Francisca ejus",
     {"corrections.json", "worklist.json", "roster.json", "dossiers.json", "searched.json", "searchindex.json"}),
    ("'Francisca bore Casparus'",
     r"Francisca bore Casparus",
     # the corrections page quotes the withdrawn sentence verbatim, as it must
     {"corrections.json", "dossiers.json", "searchindex.json"}),
    ("the chancellor called Bosponi",
     r"Bosponi",
     # searched.json and families.json name the old form in the sentence
     # that corrects it; both are telling the story of the fix
     {"corrections.json", "worklist.json", "roster.json", "dossiers.json",
      "searchindex.json", "searched.json", "families.json"}),
    ("the chaplain called Zolonta",
     r"Zolonta",
     {"corrections.json", "worklist.json", "searchindex.json"}),
    ("Antonio 'six times in ten months' left unqualified",
     r"six times in ten months(?!\s*\*\()",
     # worklist.json quotes the old count in the sentence that revises it
     {"corrections.json", "roster.json", "dossiers.json", "searchindex.json",
      "worklist.json"}),
    ("Antonio asserted dead by November 1780 (the blotted «q.m» reading)",
     r"Antonio (?:was |is )?dead by (?:\*\*)?November 1780",
     # the corrections page and the pages that tell the story of the fix quote it
     {"corrections.json", "worklist.json", "roster.json", "families.json",
      "searched.json", "dossiers.json", "searchindex.json"}),
    ("Anna Kalanj's birthplace given as the non-existent «Rijenovica»",
     r"Rijenovica",
     # roster.json quotes the withdrawn spelling on Anna Kalanj's own page, which
     # is where the story of the fix is told; kalanj.json does the same.
     {"corrections.json", "searched.json", "dossiers.json", "searchindex.json",
      "kalanj.json", "roster.json"}),
    ("Gologorica baptisms claimed to be on film",
     r"Gologorica baptisms[^\"]{0,60}on film|on film[^\"]{0,40}Gologorica",
     {"corrections.json", "worklist.json", "roster.json", "searched.json",
      "dossiers.json", "searchindex.json"}),
    # --- 29 September 2026. THREE IN ONE DAY, and all of the same shape.
    #
    # The rules above catch a WRONG CLAIM left standing. These catch the other
    # failure, which turned out to be commoner: a question the archive has
    # ANSWERED, still described somewhere as OPEN. Three times in one day a
    # session went to run a search that was already done — Fernasar/Tornasar,
    # the 1848 Reichstag roll, and the mobile sweep — because the finding was
    # written into one file and the work list still called it pending. The
    # third one was caught only because the first two had made it a habit to
    # look. And writing THESE rules turned up a fourth: the withdrawn
    # parliament claim was still the live note on Francisca Salomon in
    # ancestors.json, which is the pedigree chart a reader actually sees.
    ("the Fernasar/Tornasar reading still called unsettled",
     r"(?:which is right )?has never been settled|first thing to settle|one search from settled",
     # these quote the retired wording inside the sentence that retires it
     {"corrections.json", "worklist.json", "marriedin.json", "maternal.json",
      "dossiers.json", "searchindex.json", "searched.json"}),
    ("a Salomon asserted in the 1848 parliament",
     r"Salomon sat in the parliament",
     # corrections.json and the maternal page quote it verbatim to withdraw it
     {"corrections.json", "maternal.json", "dossiers.json", "searchindex.json",
      "worklist.json"}),
    ("pages still asserted to overflow on a phone",
     r"[Ee]ight pages still scroll sideways",
     {"corrections.json", "worklist.json", "dossiers.json", "searchindex.json"}),
    # --- 30 September 2026. The two Pazin reels were described for months as
    # covering «Gologorica, Gračišće and Lindar». All 1,463 frames were then
    # located against the films' OWN printed title cards: Lindar is not on
    # them at all — it is on ZM34K-219 and 220 — and CEROVLJE, which is, had
    # never been named anywhere in this archive. The wrong sentence was live
    # in four places at once: the Gologorica page, sources.json,
    # questions.json and the generated dossiers. Four copies of one claim is
    # exactly the shape this check was written for.
    ("the Pazin reels ZM34K-214/215 claimed to hold Lindar",
     r"Gračišće and Lindar|Gračišće and Lindar",
     # gologorica.json quotes the retired sentence verbatim inside the frame
     # map's own lead — «the description it carried … was wrong in both
     # directions» — which is where the fix is told, so it must contain it.
     {"corrections.json", "worklist.json", "dossiers.json", "searchindex.json",
      "gologorica.json"}),
    # --- 5 October 2026. The baptism register names the 1848 daughter of
    # Antonius and Francisca ROSA, born 7 June; the family tree had her as
    # «Joanna, born 9 June 1848» and this archive published that. One child,
    # not two — a mother cannot bear children two days apart. The pid is kept
    # (a moved id is a dead URL), so only the TEXT can carry the old claim.
    ("the 1848 daughter still given the tree's birth date of 9 June",
     r"9 JUN 1848|born 9 June 1848|9 June 1848",
     # corrections.json and the pages that tell the story of the fix quote it
     {"corrections.json", "worklist.json", "roster.json", "gologorica.json",
      "searched.json", "dossiers.json", "searchindex.json"}),
    ("Gregorio still given the withdrawn patronymic in a display name",
     r"Gregorio Defranceschi q\.m Antonio",
     {"corrections.json", "worklist.json", "roster.json", "families.json",
      "searched.json", "dossiers.json", "searchindex.json", "decisions.json"}),
    ("Uršula Kovačina's birth still «not found» / «about 1890», or her baptism «in the unfilmed years» (27 Oct 2026: baptised 2 Mar 1895, Crikvenica births image 652)",
     # The correction, the search log, the worklist's own narrative and the maternal page that tells
     # the story of the fix quote the old claim on purpose; generated files mirror them.
     r"Her own birth record has not been found|Uršula Kovačina, born about 1890|born about 1890, married Anton Rudolf|falls squarely in the unfilmed years|plausible window for Uršula falls in the unfilmed",
     {"corrections.json", "worklist.json", "searched.json", "maternal.json",
      "dossiers.json", "searchindex.json"}),
    ("The Kovačina–Car marriage dated 28 November 1895 (27 Oct 2026: the page reads «dne 28ª listopada» — 28 October, and Uršula was born eight months before it)",
     # The correction, the search log, the worklist's own narrative and the maternal/Crikvenica pages that tell the fix quote the old date on purpose; generated files mirror them.
     r"(?:Kovačina|Marija Car)[^\n]{0,400}28 November 1895|28 November 1895[^\n]{0,400}(?:Kovačina|Marija Car)|Her parents married in November 1895|nine months (?:after|before) (?:her|Uršula)",
     {"corrections.json", "worklist.json", "searched.json", "maternal.json", "crikvenica.json",
      "dossiers.json", "searchindex.json"}),
]

def main():
    leaks = []
    for fn in sorted(os.listdir(DATA)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(DATA, fn)
        try:
            s = json.dumps(json.load(open(path, encoding="utf-8")), ensure_ascii=False)
        except Exception:
            continue
        for label, pat, allowed in RULES:
            if fn in allowed:
                continue
            n = len(re.findall(pat, s))
            if n:
                leaks.append((fn, label, n))

    if leaks:
        print("check-propagation: FAIL — a published correction has not reached every file")
        for fn, label, n in leaks:
            print("   %-22s %-46s x%d" % (fn, label, n))
        print("\n   Either fix the file, or add it to that rule's allowed set in")
        print("   scripts/check-propagation.py and say why it quotes the error on purpose.")
        return 1

    if not RULES:
        print("check-propagation: FAIL — examined 0 corrections. A check with nothing to examine has not passed.")
        return 1
    print("check-propagation: ok — %d correction(s) reached every file that asserts them" % len(RULES))
    return 0

if __name__ == "__main__":
    sys.exit(main())
