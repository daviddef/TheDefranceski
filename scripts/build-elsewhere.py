#!/usr/bin/env python3
"""Turn the three foreign-filed FamilySearch collections into map data.

A Croatian town's registers are filed by whichever state kept them, under the
name that state used. Čakovec is «Csáktornya» in a Hungarian county inside a
collection named for Slovenia; Buje is «Buie» in an Italian one. None of that
can be found by walking a collection named for Croatia, which is why the
research map could not see any of it.

This holds the harvest, and — more importantly — the exonym table that lets the
builder put «Csáktornya» on the same dot as Čakovec.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "site", "src", "data", "fs-elsewhere.json")

# Catalogue name -> the place as it is called today. Only the ones this
# harvest actually produced; nothing is guessed for a name not in the data.
EXONYM = {
    # Međimurje and the Hungarian border districts (Zala and Vas counties)
    "Alsó-Domború": ("Donja Dubrava", "HR"), "Alsókrályevecz": ("Donji Kraljevec", "HR"),
    "Alsóvidovecz": ("Donji Vidovec", "HR"), "Bagonya": ("Bogojina", "SI"),
    "Belatincz": ("Beltinci", "SI"), "Belicza": ("Belica", "HR"),
    "Csáktornya": ("Čakovec", "HR"), "Cserföld": ("Črenšovci", "SI"),
    "Dekánovecz": ("Dekanovec", "HR"), "Domasinecz": ("Domašinec", "HR"),
    "Dráskovecz": ("Draškovec", "HR"), "Felsőhrascsán": ("Gornji Hrašćan", "HR"),
    "Felsőmihályovecz": ("Gornji Mihaljevec", "HR"), "Goricsán": ("Goričan", "HR"),
    "Gyertyámos": ("Gardinovec", "HR"), "Hodosán": ("Hodošan", "HR"),
    "Kottori": ("Kotoriba", "HR"), "Légrád": ("Legrad", "HR"),
    "Lendva-Lakos": ("Lakoš", "SI"), "Muraszerdahely": ("Mursko Središće", "HR"),
    "Nedelicz": ("Nedelišće", "HR"), "Okrugli": ("Okrugli Vrh", "HR"),
    "Perlak": ("Prelog", "HR"), "Podturen": ("Podturen", "HR"),
    "Stridó": ("Štrigova", "HR"), "Szent-Mária": ("Sveta Marija", "HR"),
    "Szent-Márton": ("Sveti Martin na Muri", "HR"), "Szoboticza": ("Subotica", "HR"),
    "Turnischa": ("Turnišče", "SI"), "Tüskeszentgyörgy": ("Sveti Juraj u Trnju", "HR"),
    "Vratisinecz": ("Vratišinec", "HR"), "Zorkóháza": ("Žiškovec", "HR"),
    "Alsólendva": ("Lendava", "SI"),
    "Bodoncz": ("Bodonci", "SI"), "Felsőlendva": ("Grad", "SI"),
    "Felsőpetrócz": ("Gornji Petrovci", "SI"), "Martyáncz": ("Martjanci", "SI"),
    "Muraszombat": ("Murska Sobota", "SI"), "Pecsarócz": ("Pečarovci", "SI"),
    "Pertócsa": ("Pertoča", "SI"), "Puczincz": ("Puconci", "SI"),
    "Tissina": ("Tišina", "SI"), "Tótkeresztur": ("Križevci", "SI"),
    "Úrdomb": ("Domanjševci", "SI"), "Vashedigkut-Tót": ("Hodoš", "SI"),
    "Vendhedigkut": ("Hodoš", "SI"), "Vizlendva": ("Večeslavci", "SI"),
    # Istria and the Trieste hinterland, filed by Italy
    "Buie": ("Buje", "HR"), "Cittanova d'Istria": ("Novigrad", "HR"),
    "Portole": ("Oprtalj", "HR"), "Verteneglio": ("Brtonigla", "HR"),
    "Materada (Frazione di Umago)": ("Materada", "HR"),
    "Isola d'Istria": ("Izola", "SI"), "Pirano": ("Piran", "SI"),
    "Muggia": ("Muggia", "IT"), "Trieste": ("Trieste", "IT"),
    "Guardiella (Frazione di Trieste)": ("Trieste", "IT"),
    "Prosecco (Frazione di Trieste)": ("Trieste", "IT"),
}

COLLECTIONS = {
    "2152685": {"title": "Italy, Pola and Trieste, Catholic Church Records, 1593–1941",
                "filed": "Italy", "key": "fs-it-pola"},
    "1985107": {"title": "Slovenia, Prekmurje and Međimurje, Civil Registers, 1895–1918",
                "filed": "Slovenia, under Hungarian county names", "key": "fs-si-mj"},
    "1875189": {"title": "Croatia, Delnice Deanery Catholic Church Books, 1571–1926",
                "filed": "Croatia, but browsable only by film", "key": "fs-hr-delnice"},
}

def main(src):
    raw = json.load(open(src, encoding="utf-8"))
    out = {"note": __doc__.strip().split("\n\n")[0],
           "collections": COLLECTIONS, "places": {}, "films": []}

    def add(cc, catname, title, wp):
        today, cc2 = EXONYM.get(catname, (catname, "HR"))
        k = f"{cc}|{catname}"
        p = out["places"].setdefault(k, {
            "cc": cc, "catalogue": catname, "today": today, "country": cc2, "books": []})
        p["books"].append({"t": title, "wp": wp})

    # Two harvests produced these, one prefixing the place with its root and
    # one not. Both shapes are accepted rather than re-running the walk.
    def place_of(key):
        return key.split("|", 1)[1] if "|" in key else key

    for key, title, wp in raw["pt"]:
        add("2152685", place_of(key), title, wp)
    for key, title, wp in raw["mj"]:
        add("1985107", place_of(key), title, wp)
    for row in raw["dl"]:
        film, images, ark = (row + ["", ""])[:3] if len(row) >= 3 else (row[0], "", row[1])
        out["films"].append({"cc": "1875189", "film": film,
                             "images": images, "ark": ark})

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    hr = sum(1 for p in out["places"].values() if p["country"] == "HR")
    print(json.dumps({"places": len(out["places"]), "croatian": hr,
                      "volumes": sum(len(p["books"]) for p in out["places"].values()),
                      "films": len(out["films"])}))

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
