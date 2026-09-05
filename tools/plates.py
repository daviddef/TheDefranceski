#!/usr/bin/env python3
"""Build web plates from the family's own scans and photographs.

Reads from the owner's document folder, writes optimised WebP into
site/public/plates/ plus a manifest at site/src/data/plates.json.

Nothing is invented here: every plate carries the archive or holder it
came from, and the caption says only what the image itself shows.
"""
import json, os, subprocess, sys

DOCS = os.path.expanduser("~/Documents/Genealogy & Family History/Defranceski")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "site", "public", "plates")
MAN  = os.path.join(ROOT, "site", "src", "data", "plates.json")

# id, source file (relative to DOCS), rotate, group, title, caption, holder
PLATES = [
 # ---- photographs, Omiš branch -------------------------------------------
 ("omis-josip-anna-ante", "Omis Branch/Omis Defranceski's/Josip and Anna with Baby Ante.jpg", 0,
  "photographs", "Josip and Anna, with Ante",
  "A studio portrait: Josip seated in a light suit and loose cravat, Anna in a dark bodice with the high collar and gathered shoulders of the 1890s, the baby Ante across her lap in a striped romper. The painted backdrop and the vignetted edge are the marks of a small provincial photographer.",
  "Family collection (Omiš branch)"),
 ("omis-zane", "Omis Branch/Omis Defranceski's/zane defranceschi.jpg", 0,
  "photographs", "Zane Defranceschi",
  "A man in a white peaked cap, shirtsleeves and wide trousers, seated on a rush-bottomed chair against a whitewashed wall, a barefoot boy leaning on his shoulder. Zane is the Venetian form of Giovanni — the same name the parish clerks wrote as Zuane.",
  "Family collection (Omiš branch)"),
 ("omis-zane-group", "Omis Branch/Omis Defranceski's/zane defranceschi middle front.jpg", 0,
  "photographs", "Zane, middle front",
  "A group photograph kept with the Omiš papers; the family's note places Zane in the middle of the front row.",
  "Family collection (Omiš branch)"),
 ("omis-anton-1932", "Omis Branch/Omis Defranceski's/Anton Toni Franceschi 1932.jpg", 0,
  "photographs", "Anton “Toni” Franceschi, 1932",
  "Dated by the family to 1932. Note the surname as written on the print: Franceschi, without the particle — the Omiš branch dropped and resumed it by turns.",
  "Family collection (Omiš branch)"),
 ("omis-frane", "Omis Branch/Omis Defranceski's/Frane Defranceski.jpg", 0,
  "photographs", "Frane Defranceski",
  "Frane is the Croatian form of Francesco; the surname on this print is spelled the Croatian way, Defranceski.",
  "Family collection (Omiš branch)"),
 ("carlo-portrait", "Seget & Istra Branch/Seget - Villa Defranceski in Istra/Carlo De Franceschi.jpg", 0,
  "photographs", "Carlo De Franceschi in old age",
  "The historian of Istria, born at Gologorica in 1809, photographed late in life: round spectacles, white beard, dark stock. He died in 1893.",
  "Reproduced in the Seget monograph"),

 # ---- displaced-persons portraits, Crikvenica family ---------------------
 ("fiche-petar", "Peter Defranceski/peter/a.jpg", 0,
  "dp", "Petar Defranceski — Fiche Individuelle",
  "The French-zone camp card. Petar, born 15 June 1913 at Crikvenica, Yugoslav, profession auto-mécanicien, employer's address Kelterstr. 30 Neuhausen, married. Five fingerprints in red, a passport photograph clipped at the top right, file 148.902 / 30609.",
  "International Tracing Service / Arolsen Archives"),
 ("fiche-zdravko", "Peter Defranceski/peter/400.jpg", 0,
  "dp", "Zdrafko Defranceski — Fiche Individuelle",
  "Born 1 April 1921, Yugoslav, auto-mécanicien, married. File 148.901 / 30560. The same trade as Petar, and the same camp office.",
  "International Tracing Service / Arolsen Archives"),
 ("fiche-ruza", "Peter Defranceski/peter/800.jpg", 0,
  "dp", "Ruža Defranceski — Fiche Individuelle",
  "Born 1922, no profession recorded, married. In the photograph she wears a cross at her throat and holds her infant son, who is not named here: he was born in 1944 and may be living.",
  "International Tracing Service / Arolsen Archives"),

 # ---- the wartime and displaced-persons paper ---------------------------
 ("its-pfullingen-list", "Peter Defranceski/peter/000.jpg", 0,
  "documents", "Foreigners registered at Pfullingen, 1939–45",
  "“Aufstellung über die in der Zeit vom 1. Sept. 1939 – 25. April 1945 in der Vorstadt Pfullingen gemeldet gewesenen Ausländer. Hier: Kroatien.” Drawn up at Reutlingen-Pfullingen on 10 March 1947. Six Defranceskis are listed, five of them born at Crikvenica.",
  "International Tracing Service / Arolsen Archives"),
 ("its-cover", "Peter Defranceski/peter/1050.jpg", 0,
  "documents", "ITS file cover D-1.505",
  "The tracing-service wrapper for the family: Petar, his wife Luise née Salzer of Neuhausen, and two daughters born at Urach and Metzingen during the war.",
  "International Tracing Service / Arolsen Archives"),
 ("cm1-identity", "Peter Defranceski/peter/1051.jpg", 0,
  "documents", "CM/1 application, identity page",
  "The IRO care-and-maintenance application, 7 November 1947. Petar gives his nationality at birth as Austria-Hungary, his address as Kelternstr. 30 Neuhausen, and the country he wants to be resettled in as the United States — California.",
  "International Tracing Service / Arolsen Archives"),
 ("cm1-detail", "Peter Defranceski/peter/1052.jpg", 0,
  "documents", "CM/1 application, history page",
  "Residences, trades and schooling: Split 1937–39 with Jugoslav Lloyd as a ship's engineer, then Germany from April 1939; car-mechanic examination at Reutlingen in 1947; a truck valued at 15,000 among his assets; and an aunt, Jacomina Alafetić, at San Pedro, California.",
  "International Tracing Service / Arolsen Archives"),
 ("kk-felix", "Peter Defranceski/peter/1000.jpg", 0,
  "documents", "Felix Defranceski — sickness-fund card",
  "Felix, born 1908 at Crikvenica, single, living at Pfullingerlandstraße in Reutlingen. Employers from July 1941: Hermann Sauer of Pfullingen as a motor mechanic, then Wilhelm Heim as a driver, then Sauer again.",
  "International Tracing Service / Arolsen Archives"),
 ("kk-ivan", "Peter Defranceski/peter/1002.jpg", 0,
  "documents", "Ivan Defranceski — sickness-fund card",
  "Ivan, born June 1925 at Crikvenica, single, Brunnenstraße 7, Pfullingen. He entered work on 21 October 1941, aged sixteen, as a Hilfsarbeiter — an unskilled hand.",
  "International Tracing Service / Arolsen Archives"),
 ("kk-petar", "Peter Defranceski/peter/1003.jpg", 0,
  "documents", "Petar Defranceski — sickness-fund card",
  "Marked “Kroate” in the top margin. Employed by Hermann Sauer of Reutlingen on motor-vehicle repairs from 1 April 1942 to 2 March 1945 — the card runs out three weeks before the French army reached the town.",
  "International Tracing Service / Arolsen Archives"),
 ("kk-zdravko", "Peter Defranceski/peter/1005.jpg", 0,
  "documents", "Zdravko Defranceski — sickness-fund card",
  "Below the employment lines, a clerk has pencilled a short life: in Croatia 1936–43; taken by the Partisans in 1943; three or four months in captivity; then straight to Germany.",
  "International Tracing Service / Arolsen Archives"),
 ("cert-anton-1890", "Peter Defranceski/peter/1006.jpg", 0,
  "documents", "Anton Defranceski, born 1890 — municipal certificate",
  "Certified by the mayor of Pfullingen, Kreis Reutlingen, on 28 February 1950: Anton Defranceski, born 20 January 1890 at Crikvenica, Croatia-Yugoslavia, lodged at Pfullingen, workplace Hermann Sauer, Reutlingen-Süd.",
  "International Tracing Service / Arolsen Archives"),
 ("roll-1949", "Peter Defranceski/peter/1100.jpg", 0,
  "documents", "Resettlement roll, February 1949",
  "Lines 58–60 of a nominal roll dated 22 February 1949: Zdrafko, Ruža and their son, Yugoslavs from Crikvenica and Fužine, at Reutlingen, with IRO numbers against each name.",
  "International Tracing Service / Arolsen Archives"),

 # ---- Gračišće: the parish record of the direct line -----------------
 ("dapa-letter-1", "Unsorted Scan - [Unread] Epson_27072021203248.jpg", 0,
  "gracisce", "Državni arhiv u Pazinu to David Defranceski, 26 April 2021",
  "The Pazin State Archive answers a request made eight days earlier: the copy from the Gračišće birth register for Josip Defranceschi is enclosed. Itemised at 117 kuna — research 50, certified A3 copy 7, overseas postage 60.",
  "Državni arhiv u Pazinu (DAPA)"),
 ("gracisce-1863", "Unsorted Scan - [Unread] Epson_27072021203422.jpg", 0,
  "gracisce", "Liber Baptizatorum, Gračišće 1841–1899",
  "Certified and stamped by the Pazin State Archive. The register is ruled for house number, the child's name and date of birth, religion, sex, legitimacy, both parents with the father's condition, the godparents and the midwife. The entry taken out for this family is Josephus, born 22 March 1863, son of Antonius Defranceschi, lapicida — a stonecutter.",
  "Državni arhiv u Pazinu (DAPA), MKR Gračišće 1841–1899"),
 ("dapa-letter-2", "Unsorted Scan - [Unread] Epson_27072021203523.jpg", 0,
  "gracisce", "Državni arhiv u Pazinu, 24 June 2021",
  "A second answer, this time for Antonius Defranceschi and his family, and for Giovanni Battista Defranceschi and his family — the two Status Animarum entries opposite. 124 kuna.",
  "Državni arhiv u Pazinu (DAPA)"),
 ("status-animarum-gb", "Unsorted Scan - [Unread] Epson_27072021203744.jpg", 90,
  "gracisce", "Status Animarum — house 5, Gallignana",
  "The book of souls for the parish of Gallignana. House 5: Joan. Bapt. Defranceschi, agricola, born 13 August 1787, married 1819, died 1 September 1846; his wife Francisca Salomon, born 17 March 1797; and their sons Raymundus, Antonius, Joannes and Franciscus.",
  "Državni arhiv u Pazinu (DAPA), ZM34K 217, M01072071"),
 ("status-animarum-ant", "Unsorted Scan - [Unread] Epson_27072021203849.jpg", 90,
  "gracisce", "Status Animarum — house 19, Gallignana",
  "House 19: † Antonius Defranceschi q. Joannis — son of the late Giovanni — born 20 September 1825, married 25 November 1856, died 4 August 1894; his wife Maria née Fernasar, born 17 October 1832; and their children Antonius, Josephus, Leopolda, Catharina and Modestus.",
  "Državni arhiv u Pazinu (DAPA), ZM34K 217, M01071656"),

 # ---- the Vinodol and Pazin registers ------------------------------------
 ("ana-kalanj", "Birth, Death & Marriage Records/Ana Kalanj Defranceski Birth.jpg", 0,
  "gracisce", "Anna Kalanj, born 3 January 1864",
  "Entry 2 for 1864 in the baptismal register of Ledenice, the Vinodol parish above Crikvenica. Anna, legitimate, daughter of Josephus Kalanj and Rosalia née Perković, at Rijenovica house 22; godparents Josephus Ban and his wife Anna; baptised by Vincentius Segulja, parish priest. The other entries on the page are Perković, Butković, Mataija, Semper — the surnames of one valley.",
  "Državni arhiv / matične knjige, Ledenice"),
 ("carlo-witness", "Birth, Death & Marriage Records/antonio Covaz : Covach Marriage.jpg", 0,
  "documents", "Carlo De Franceschi signs as a witness, Pazin 1842",
  "The Pisino marriage register, 13 September 1842. Antonius Covach, 22, of house 33, marries Hedwiges Mrak, 17, of house 30. In the column for witnesses: «Carolus Defranceschi» and «Aegidius Mrach», and against their names their conditions — «I. R. Auscultans» and «studiosus». Imperial-Royal Auscultator was the entry rank of the Austrian judicial service. Carlo was thirty-two.",
  "Hrvatski državni arhiv, HDA 583"),
 ("anton-1890", "Birth, Death & Marriage Records/Anton rudolph birth.png", 0,
  "gracisce", "Anton Rudolf, born 20 January 1890",
  "Entry 9 in the Croatian-language baptismal register: Anton Rudolf, born 20 January 1890, baptised 9 February, legitimate, son of «Josip Defranceschi i žena Ana Kalanj rodjena». Residence: Klenovica house 22 — and beside it, in the column for the parents' place of origin, «Gallignana u Istriji». Godfather Jakov Kalanj of the same house 22; baptised by Matej Butković, parish priest.",
  "Matične knjige, Ledenice / Klenovica"),
 ("nodburga-1794", "Birth, Death & Marriage Records/Nodburgam defranceschi.png", 0,
  "documents", "Nodburga Defranceschi marries at Bakar, 1794",
  "27 February 1794, dispensed from the third banns by the Bishop: in the church of the Blessed Virgin Mary, the marriage of Dominus Joannes Vorkret and Domicella Nodburga Defranceschi, blessed by Canon Antonius de Agnesis, in the presence of the Vice-Governor Aloysius de Orlando and the noble Antonio Maria ab Orebich, assessor of the community of Buccari. Notburga is a Tyrolean saint's name, and an odd one to find on the Kvarner coast.",
  "Matične knjige, Bakar (Buccari)"),
 ("cm1-zara", "Birth, Death & Marriage Records/001.jpg", 0,
  "dp", "Antonio Defranceschi of Zara — refused",
  "A second IRO application, completed at Bolzano on 10 May 1950. Antonio Defranceschi, born 18 January 1905 at Zara, ethnic group Italian, son of Riccardo and Giuseppina Zersuscek; his wife Antonietta née Stipanovich, born 1910, daughter of Sabino Stipanovich and Maria Lovrich. Clerk at Zara to 1941, then a soldier in the Italian army until the capitulation, then Zara again until January 1944, then Italy. Twice across the form, in blue crayon: NOT WITHIN THE MANDATE OF IRO.",
  "International Tracing Service / Arolsen Archives"),
 # ---- other holdings -----------------------------------------------------
 ("omis-chart", "Research & Historical Documents/franceschi omis - family tree.jpg", 0,
  "documents", "The Omiš descent chart",
  "A hand-compiled chart of the Omiš and Zadar family, twenty generations deep, running from the fourteenth century to the twentieth. The later generations are omitted from this archive because the people in them may be living.",
  "Family collection (Omiš branch)"),
 ("bakar-1783", "Research & Historical Documents/ defranceschi 1783 bakar.png", 0,
  "documents", "Defranceschi at Bakar, 1783",
  "A register page kept with the family's research notes, placing the name at Bakar on the Kvarner coast in 1783.",
  "Family research collection"),
 ("moncalvo", "Research & Historical Documents/moncalvo.jpg", 0,
  "places", "Moncalvo di Pisino",
  "Gologorica under its Italian name — Moncalvo in the county of Pazin, where Carlo De Franceschi was born in 1809.",
  "Family research collection"),
 ("seget-view", "Research & Historical Documents/seget.jpeg", 0,
  "places", "Seget, near Umag",
  "The western-Istrian estate of the other branch, which reached Istria from Crete after the Candian War ended in 1669.",
  "Family research collection"),
]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        sys.stderr.write(" ".join(cmd[:3]) + " FAILED: " + r.stderr.decode()[:200] + "\n")
        return False
    return True

def main():
    os.makedirs(OUT, exist_ok=True)
    man, missing = [], []
    for pid, rel, rot, group, title, caption, holder in PLATES:
        src = os.path.join(DOCS, rel)
        if not os.path.exists(src):
            missing.append(rel); continue
        full = os.path.join(OUT, pid + ".webp")
        thumb = os.path.join(OUT, pid + "-t.webp")
        rotate = ["-rotate", str(rot)] if rot else []
        ok  = run(["magick", src, "-auto-orient"] + rotate +
                  ["-resize", "1800x1800>", "-quality", "82", full])
        ok &= run(["magick", src, "-auto-orient"] + rotate +
                  ["-resize", "700x700>", "-quality", "78", thumb])
        if not ok: continue
        w = h = 0
        try:
            out = subprocess.run(["magick", "identify", "-format", "%w %h", full],
                                 capture_output=True).stdout.decode().split()
            w, h = int(out[0]), int(out[1])
        except Exception:
            pass
        man.append({"id": pid, "group": group, "title": title, "caption": caption,
                    "holder": holder, "w": w, "h": h,
                    "src": f"/plates/{pid}.webp", "thumb": f"/plates/{pid}-t.webp"})
        print("ok", pid, f"{w}x{h}")
    json.dump(man, open(MAN, "w"), indent=1, ensure_ascii=False)
    print(f"\n{len(man)} plates -> {MAN}")
    if missing:
        print("MISSING:"); [print("  ", m) for m in missing]

if __name__ == "__main__":
    main()
