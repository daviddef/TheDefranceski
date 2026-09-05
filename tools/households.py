"""Reconstruct households from indexed baptism/burial records.

A household is a (father, mother) pair. Records name their parents, so grouping
records by a normalised parent pair recovers the sibling set. Latin case endings
and spelling drift mean the normaliser does most of the work.
"""
import csv, json, re, unicodedata
from collections import defaultdict

OURS = re.compile(r'franceschi|franceski|franzeschi|francheschi', re.I)

# Latin/Italian/Croatian forms of the same given name
CANON = {
 'giovanni': 'joannes joannem joanni joannis joannem gioannes gioanni zuanne zuane zuanne giovanni ivan johann johannes joan gio giovan nep',
 'battista': 'battista batta baptista baptae bapt batista bata',
 'antonio':  'antonio antonius antonium antonii anto anton',
 'antonia':  'antonia antoniae antoniæ anta antonietta',
 'matteo':   'matteo mattio matio mattheus mathaeus mathæus mathæi matheus mattia matthia mateo',
 'francesco':'francesco franciscus francisci franciscum franco franz francescho',
 'francesca':'francesca francisca franciscae franciscæ franca franceschina',
 'pietro':   'pietro pier piero pieto petrus petrum petri',
 'valentino':'valentino valentinus valentini valentinum valentio valentin',
 'giuseppe': 'giuseppe josephus josephi joseph josef',
 'giuseppa': 'giuseppa josepha josepham josephae',
 'maria':    'maria mariam mariæ mariae marie marietta',
 'elena':    'elena ellena helena helenæ helena elenam ellenam',
 'orsola':   'orsola ursula ursulæ ursulam ursulae',
 'domenico': 'domenico dominicus domco domco',
 'domenica': 'domenica dominica domca domča domenicae dominicae doma',
 'gasparo':  'gasparo gaspero gaspo gaspar gasparus gasparina',
 'nicolo':   'nicolo niccolo nicolaus nicolaa nicoló nicolò nicolaus',
 'vittorio': 'vittorio victorius vitorio victorii vitorii vitnio',
 'vittoria': 'vittoria victoria vittoriam',
 'caterina': 'caterina catharina cattarina catterina katarina catharinam catharinæ',
 'bartolo':  'bartolo bortolo bartholomaeus bartholomaei barthol',
 'lucia':    'lucia luciae luciæ lutia',
 'anna':     'anna annam annæ anta anzoletta',
 'stella':   'stella stela steffa etella',
 'gregorio': 'gregorio gregorius gregorii',
 'natale':   'natale nadal natalis nataliem',
 'stefano':  'stefano stephanus stephanus steffano',
 'agata':    'agata agatha agathæ',
 'eufemia':  'eufemia euphemia euphemię euphemiae',
 'giacomo':  'giacomo jacobus',
 'giacoma':  'giacoma jacobina jacoba',
 'andrea':   'andrea andreas andreæ andra andrae',
 'luca':     'luca lucas',
 'paolo':    'paolo paola paulus paoli',
 'carlo':    'carlo carolus caroli karlo',
 'michele':  'michele michiel michaelis michiele michael',
 'teresa':   'teresa theresia teresia theresiam',
}
LOOKUP = {}
for k, v in CANON.items():
    for form in v.split():
        LOOKUP[form] = k

# one town, several names in the index
PLACE_CANON = {'Vitipolis':'Rijeka','Fiume':'Rijeka','Almissa':'Omiš','Spalato':'Split','Pola':'Pula',
               'Dignano':'Vodnjan','Parenzo':'Poreč','Rovigno':'Rovinj','Pisino':'Pazin','Fasana':'Fažana',
               'Sanvincenti':'Svetvinčenat','Gallignana':'Gračišće','Pedena':'Pićan','Albona':'Labin'}
VAGUE_PLACE = {'','Croazia','Hrvatska','Kraljevina Hrvatska','Regnum Croatiae','Croatia-Slavonia',
               'Österreich','Austria','Italia'}

def canon_place(p):
    p = (p or '').split(',')[0].strip()
    return PLACE_CANON.get(p, p)

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def norm_token(t):
    t = strip_accents(t.lower()).strip('.,')
    return LOOKUP.get(t, t)

def parse_person(full):
    """Return (given_key, surname_is_ours, display)."""
    full = re.sub(r'\s+', ' ', (full or '').strip())
    if not full:
        return None
    toks = full.split()
    ours = bool(OURS.search(full))
    # drop the family surname tokens; keep the rest as given names
    given = [t for t in toks if not OURS.search(t)]
    if not given:
        given = toks[:1]
    key = ' '.join(norm_token(t) for t in given[:2])
    return key, ours, full

def year(*vals):
    for v in vals:
        m = re.search(r'\b(1[5-9]\d\d|20\d\d)\b', v or '')
        if m:
            return int(m.group(1))
    return None

REGION_OF = {
 'Rijeka':'kvarner','Bakar':'kvarner','Kastav':'kvarner','Volosko':'kvarner','Opatija':'kvarner',
 'Crikvenica':'kvarner','Senj':'kvarner','Krk':'kvarner','Ledenice':'kvarner','Lovran':'kvarner',
 'Omiš':'dalmatia','Split':'dalmatia','Imotski':'dalmatia','Postira':'dalmatia','Makarska':'dalmatia',
 'Pazin':'istria','Gračišće':'istria','Gologorica':'istria','Pićan':'istria','Poreč':'istria',
 'Rovinj':'istria','Pula':'istria','Vodnjan':'istria','Ližnjan':'istria','Fažana':'istria',
 'Promontore':'istria','Sterna':'istria','Fianona':'istria','Sovignacco':'istria','Kaštelir':'istria',
 'Svetvinčenat':'istria','Motovun':'istria','Vižinada':'istria','Barban':'istria','Umag':'istria','Tar':'istria',
}
def region_of(place, src):
    r = REGION_OF.get(place)
    if r:
        return r
    # an unlocalised Croatian record could be anywhere; an Austrian one could not
    return 'austria' if src == 'austria' else ''

def load(path, src):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    for r in rows: r['_src'] = src
    return rows

MALE = {'giovanni','battista','antonio','matteo','francesco','pietro','valentino','giuseppe','domenico',
        'gasparo','nicolo','vittorio','bartolo','gregorio','natale','stefano','giacomo','andrea','luca',
        'paolo','carlo','michele','martino','tomaso','angelo','ignazio','simone','felice','luigi'}
FEMALE = {'maria','elena','orsola','caterina','lucia','anna','stella','agata','eufemia','teresa','domenica',
          'francesca','giovanna','margarita','marta','antonia','vittoria','zuanna','giustina','madalena',
          'maddalena','filomena','veneranda','pasqua','fioretta','colotta','bonetta','zacchera','giacoma',
          'giuseppa','perina','petrina','stella','irene','agatha','lamberta','virginia','aurelia','nicolaa'}

def sex_of(key):
    first = (key or '').split()[0] if key else ''
    if first in MALE: return 'M'
    if first in FEMALE: return 'F'
    return '?'

def lev(a, b):
    if a == b: return 0
    if abs(len(a) - len(b)) > 2: return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def build(rows):
    houses = defaultdict(lambda: {'father': None, 'mother': None, 'fatherKey': '', 'motherKey': '',
                                  'children': [], 'places': defaultdict(int), 'years': []})
    for r in rows:
        parents = [p.strip() for p in (r['parents'] or '').split('&') if p.strip()]
        if len(parents) < 1:
            continue
        pf = [parse_person(p) for p in parents]
        pf = [p for p in pf if p]
        if not pf:
            continue
        # the parent carrying the family surname is taken as the father
        fathers = [p for p in pf if p[1]]
        mothers = [p for p in pf if not p[1]]
        f = fathers[0] if fathers else pf[0]
        m = mothers[0] if mothers else (pf[1] if len(pf) > 1 else None)
        fk, mk = f[0], (m[0] if m else '')
        if not mk or fk == mk:
            continue  # index gave the same person twice; no household recoverable
        place = canon_place(r['place'])
        key = (frozenset((fk, mk)), '' if place in VAGUE_PLACE else place)
        h = houses[key]
        # decide which is which: given-name gender first, family surname second
        cand = [(fk, f[2], f[1]), (mk, m[2], m[1])]
        sexes = [sex_of(c[0]) for c in cand]
        if 'M' in sexes and 'F' in sexes:
            dad = cand[sexes.index('M')]; mum = cand[sexes.index('F')]
        elif cand[0][2] != cand[1][2]:
            dad = cand[0] if cand[0][2] else cand[1]
            mum = cand[1] if cand[0][2] else cand[0]
        else:
            dad, mum = cand[0], cand[1]
        if not h['father']: h['father'] = dad[1]; h['fatherKey'] = dad[0]
        if not h['mother']: h['mother'] = mum[1]; h['motherKey'] = mum[0]
        y = year(r['birth'], r['christening'], r['death'], r['burial'])
        ck = parse_person(r['name'])
        h['region'] = h.get('region') or region_of(place, r.get('_src',''))
        h['children'].append({'name': r['name'], 'sex': r['sex'], 'birth': r['birth'],
                              'death': r['death'] or r['burial'], 'place': r['place'], 'y': y, 'id': r['id'],
                              'key': ck[0] if ck else '', 'ours': bool(ck and ck[1]),
                              'by': year(r['birth'], r['christening']),
                              'dy': year(r['death'], r['burial'])})
        if place and place not in VAGUE_PLACE:
            h['places'][place] += 1
        if y:
            h['years'].append(y)
    out = []
    for (keyset, _place), h in houses.items():
        # de-duplicate children that are the same person indexed twice
        seen, kids = set(), []
        for c in sorted(h['children'], key=lambda c: (c['y'] or 9999)):
            sig = (re.sub(r'\s+', ' ', c['name'].lower()), c['y'])
            if sig in seen:
                continue
            seen.add(sig)
            kids.append(c)
        if not h['mother'] or len(kids) < 2:
            continue
        place = max(h['places'].items(), key=lambda x: x[1])[0] if h['places'] else ''
        out.append({'key': ' + '.join(sorted(keyset)), 'fatherKey': h['fatherKey'], 'motherKey': h['motherKey'],
                    'father': h['father'], 'mother': h['mother'],
                    'place': place, 'region': h.get('region',''),
                    'from': min(h['years']) if h['years'] else None,
                    'to': max(h['years']) if h['years'] else None,
                    'n': len(kids), 'children': kids})
    # merge households whose mother's surname is only a spelling apart
    merged = []
    for h in sorted(out, key=lambda x: (x['key'], x['from'] or 9999)):
        hit = None
        for m2 in merged:
            if m2['fatherKey'] != h['fatherKey']:
                continue
            if m2['place'] and h['place'] and m2['place'] != h['place']:
                continue
            if m2.get('region') and h.get('region') and m2['region'] != h['region']:
                continue
            # the mother decides. Where her maiden name survives, compare surnames;
            # where the index gave her the family surname it carries no information,
            # so the normalised given name has to match exactly.
            ma, mb = (m2['mother'] or ''), (h['mother'] or '')
            sa, sb = ma.lower().split()[-1], mb.lower().split()[-1]
            family_a, family_b = bool(OURS.search(sa)), bool(OURS.search(sb))
            if family_a or family_b:
                same = m2['motherKey'] == h['motherKey']
            else:
                same = lev(sa, sb) <= 2
            if same:
                hit = m2; break
        if hit:
            if not hit['place'] and h['place']:
                hit['place'] = h['place']
            seen = {(re.sub(r'\s+', ' ', c['name'].lower()), c['y']) for c in hit['children']}
            for c in h['children']:
                sig = (re.sub(r'\s+', ' ', c['name'].lower()), c['y'])
                if sig not in seen:
                    hit['children'].append(c); seen.add(sig)
            hit['children'].sort(key=lambda c: (c['y'] or 9999))
            hit['n'] = len(hit['children'])
            ys = [c['y'] for c in hit['children'] if c['y']]
            hit['from'], hit['to'] = (min(ys), max(ys)) if ys else (None, None)
        else:
            merged.append(h)
    merged = [h for h in merged if h['n'] >= 2]
    merged.sort(key=lambda h: (h['from'] or 9999, -h['n']))
    for i, h in enumerate(merged):
        h['id'] = f'h{i:03d}'
    return merged

if __name__ == '__main__':
    rows = load('data/familysearch-croatia.csv', 'croatia') + load('data/familysearch-austria.csv', 'austria')
    hs = build(rows)
    json.dump(hs, open('site/src/data/households.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(rows)} records -> {len(hs)} households with 2+ children')
    for h in hs[:16]:
        print(f"  {h['n']:>2}  {h['father'][:34]:<34} + {h['mother'][:26]:<26} {h['place'][:14]:<14} {h['from']}–{h['to']}")
