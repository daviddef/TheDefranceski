"""Reconstruct households from indexed baptism/burial records.

A household is a (father, mother) pair. Records name their parents, so grouping
records by a normalised parent pair recovers the sibling set. Latin case endings
and spelling drift mean the normaliser does most of the work.
"""
import csv, json, re, unicodedata
from collections import defaultdict

# the surname, but not the given names Franceschina/Franceschino nor the
# separate family Franceschini/Franceschinis
OURS = re.compile(r'(?:franceschi|franceski|franzeschi|francheschi)(?![a-z])', re.I)

# Latin/Italian/Croatian forms of the same given name
CANON = {
 # Each line: one person, however four languages and three centuries wrote them.
 # Latin (register) · Italian · Venetian · Croatian · German · English
 'giovanni': 'giovanni giovan gio giovanni joannes joannem joanni joannis gioannes gioanni ioannes '
             'zuane zuanne nane ivan ivo ive johann johannes hans john joan nep giovanbattista '
             'gioannis gioanne ioannis ianni zanne zan',
 'battista': 'battista batta baptista baptae bapt batista bata krstitelj',
 'antonio':  'antonio antonius antonium antonii anto anton ante antun toni anthony antal antony antonÿ',
 'antonia':  'antonia antoniae antoniæ anta antonietta antonija',
 'matteo':   'matteo mattio matio mattheus mathaeus mathæus mathæi matheus mate matij matthew mathias matija',
 'francesco':'francesco franciscus francisci franciscum franco franz francescho frane franjo frank francis checo',
 'francesca':'francesca francisca franciscae franciscæ franca franka franica frances',
 'pietro':   'pietro pier piero pieto petrus petrum petri petar pere peter petar',
 'valentino':'valentino valentinus valentini valentinum valentio valentin valentine',
 'giuseppe': 'giuseppe josephus josephi joseph josef josip bepo bepi jozo joso pepi',
 'giuseppa': 'giuseppa josepha josepham josephae josipa josephine',
 'maria':    'maria mariam mariæ mariae marie marietta marija mare mary marija',
 'elena':    'elena ellena helena helenæ elenam ellenam jelena helen ilona',
 'orsola':   'orsola ursula ursulæ ursulam ursulae ursa uršula',
 'domenico': 'domenico dominicus domco menego dominik dominic',
 'domenica': 'domenica dominica domca domča domenicae dominicae doma dominika',
 'gasparo':  'gasparo gaspero gaspo gaspar gasparus gaspare jasper',
 'gasparina':'gasparina gasperina',
 'nicolo':   'nicolo niccolo nicolaus nicolaa nicoló nicolò nikola nicholas nikolaus mikula miko',
 'vittorio': 'vittorio victorius vitorio victorii vitorii vitnio viktor victor',
 'vittoria': 'vittoria victoria vittoriam viktorija',
 'caterina': 'caterina catharina cattarina catterina katarina catharinam catharinæ kate katharina catherine kata',
 'bartolo':  'bartolo bortolo bartholomaeus bartholomaei barthol bartol bartolomeo bartholomew',
 'lucia':    'lucia luciae luciæ lutia luce lucija lucy',
 'anna':     'anna annam annæ anta anzoletta ana ane anne',
 'stella':   'stella stela steffa etella zvijezda',
 'gregorio': 'gregorio gregorius gregorii grgur gregory',
 'natale':   'natale nadal natalis nataliem bozo božo noel',
 'stefano':  'stefano stephanus steffano stjepan stipe stipan stephen steven stefan',
 'agata':    'agata agatha agathæ agneza',
 'eufemia':  'eufemia euphemia euphemię euphemiae fuma fumia fumija',
 'giacomo':  'giacomo jacobus jakov jakob james jacob jacomo',
 'giacoma':  'giacoma jacobina jacoba jakovina',
 'andrea':   'andrea andreas andreæ andra andrae andrija andrew andre',
 'luca':     'luca lucas luka luke',
 'paolo':    'paolo paulus paoli pavao pavle paul',
 'carlo':    'carlo carolus caroli karlo karl charles carl',
 'michele':  'michele michiel michaelis michiele michael mijo miho mihovil mihael',
 'teresa':   'teresa theresia teresia theresiam terezija theresa',
 'marco':    'marco marcus marko mark',
 'vincenzo': 'vincenzo vincentius vincentii vinko vincent vinzenz',
 'lorenzo':  'lorenzo laurentius laurentii lovro lovre lawrence lorenz',
 'martino':  'martino martinus martin',
 'tomaso':   'tomaso thomas tommaso toma tomo tomislav',
 'angelo':   'angelo angelus andjelo anđelo angel',
 'simone':   'simone simon simeon sime šime',
 'filippo':  'filippo philippus filip philip',
 'girolamo': 'girolamo hieronymus jerolim jere momolo jerome',
 'margarita':'margarita margaretha margherita margareta marta margaret',
 'giovanna': 'giovanna joanna johanna ivana jovana jane joan',
 'madalena': 'madalena maddalena magdalena magdalene mande manda',
 'rosa':     'rosa rosina ruza ruža rose',
 'filomena': 'filomena philomena fila',
 'veneranda':'veneranda venera',
 'pasqua':   'pasqua paschalis pasqualina pasko paško',
 'benedetto':'benedetto benedictus benko benedict',
 'ignazio':  'ignazio ignatius ignac ignatz',
 'luigi':    'luigi aloysius aloisio alois alojz louis lewis',
 'felice':   'felice felix srecko srećko',
 'urbano':   'urbano urbanus urban',
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

# nobiliary and connective particles are not given names
PARTICLES = {'de', 'di', 'da', 'del', 'della', 'dei', 'degli', 'dal', 'von', 'van', 'y', 'or', 'o'}
# Latin declension endings, longest first
LATIN_ENDINGS = ('issimus', 'orum', 'arum', 'ibus', 'ium', 'ii', 'is', 'us', 'um', 'am',
                 'ae', 'os', 'as', 'es', 'em', 'e', 'i', 'a', 'o')

def norm_token(t):
    t = strip_accents(t.lower()).strip('.,;:')
    if not t or t in PARTICLES:
        return ''
    if t in LOOKUP:
        return LOOKUP[t]
    # try again with Latin case endings peeled off, longest ending first
    for end in LATIN_ENDINGS:
        if len(t) > len(end) + 2 and t.endswith(end):
            stem = t[:-len(end)]
            for probe in (stem, stem + 'o', stem + 'us', stem + 'a', stem + 'e', stem + 'es', stem + 'i'):
                if probe in LOOKUP:
                    return LOOKUP[probe]
    return t

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
    parts = [n for n in (norm_token(t) for t in given) if n]
    if not parts:
        parts = [strip_accents(given[0].lower())]
    key = ' '.join(parts[:2])
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

MALE = {'giovanni','battista','antonio','matteo','francesco','pietro','valentino','giuseppe',
        'domenico','gasparo','nicolo','vittorio','bartolo','gregorio','natale','stefano','giacomo',
        'andrea','luca','paolo','carlo','michele','marco','vincenzo','lorenzo','martino','tomaso',
        'angelo','simone','filippo','girolamo','benedetto','ignazio','luigi','felice','urbano'}
FEMALE = {'maria','elena','orsola','caterina','lucia','anna','stella','agata','eufemia','teresa',
          'domenica','francesca','giovanna','margarita','antonia','vittoria','giustina','madalena',
          'filomena','veneranda','pasqua','giacoma','giuseppa','gasparina','rosa','perina','petrina',
          'irene','lamberta','virginia','aurelia','zuanna','fioretta','colotta','bonetta','zacchera'}

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
        ours = bool(OURS.search(h['father'] or '')) or bool(OURS.search(h['mother'] or ''))
        if not ours:
            continue
        place = max(h['places'].items(), key=lambda x: x[1])[0] if h['places'] else ''
        out.append({'key': ' + '.join(sorted(keyset)), 'fatherKey': h['fatherKey'], 'motherKey': h['motherKey'],
                    'father': h['father'], 'mother': h['mother'],
                    'place': place, 'region': h.get('region',''),
                    'line': 'male' if OURS.search(h['father'] or '') else 'female',
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
    rows = (load('data/familysearch-croatia.csv', 'croatia')
            + load('data/familysearch-austria.csv', 'austria')
            + load('data/familysearch-inlaws.csv', 'croatia'))
    hs = build(rows)
    json.dump(hs, open('site/src/data/households.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(rows)} records -> {len(hs)} households with 2+ children')
    for h in hs[:16]:
        print(f"  {h['n']:>2}  {h['father'][:34]:<34} + {h['mother'][:26]:<26} {h['place'][:14]:<14} {h['from']}–{h['to']}")
