"""Link reconstructed households into lineages.

A household H is the child of household P when a recorded child of P grew up to be
the father (or, rarely, the mother) named in H. The evidence is a name match on the
normalised given name, a plausible generation gap, a compatible parish, and the
child not having died young. Ambiguity is reported, not resolved.
"""
import json, re
from collections import defaultdict

VAGUE = {'', 'Croazia', 'Hrvatska', 'Kraljevina Hrvatska', 'Regnum Croatiae',
         'Croatia-Slavonia', 'Österreich', 'Austria'}
# places that are the same town under different names
SAME = {'Vitipolis': 'Rijeka', 'Fiume': 'Rijeka', 'Almissa': 'Omiš', 'Spalato': 'Split',
        'Pola': 'Pula', 'Dignano': 'Vodnjan', 'Parenzo': 'Poreč'}

def place_key(p):
    p = (p or '').strip()
    return SAME.get(p, p)

def compatible(a, b):
    a, b = place_key(a), place_key(b)
    if a in VAGUE or b in VAGUE:
        return 1          # unknown — allowed, but unscored
    return 2 if a == b else 0

def first(key):
    return (key or '').split()[0] if key else ''

def candidates(hs):
    """For each household, find the parent household its father came from."""
    links, ambiguous = [], []
    by_id = {h['id']: h for h in hs}
    for h in hs:
        fk = first(h['fatherKey'])
        if not fk or not h.get('from'):
            continue
        scored = []
        for p in hs:
            if p['id'] == h['id']:
                continue
            if p.get('region') and h.get('region') and p['region'] != h['region']:  # both known and different
                continue          # no cross-region descent on a bare name match
            pc = compatible(p['place'], h['place'])
            if pc == 0:
                continue
            for c in p['children']:
                if first(c['key']) != fk:
                    continue
                if c['sex'] == 'Female':
                    continue
                if not c['by']:
                    continue
                gap = h['from'] - c['by']
                if not (17 <= gap <= 48):
                    continue
                if c['dy'] and c['by'] and (c['dy'] - c['by']) < 15:
                    continue          # died before he could be a father
                s = pc
                if len(c['key'].split()) > 1 and len(h['fatherKey'].split()) > 1 \
                   and c['key'].split()[1] == h['fatherKey'].split()[1]:
                    s += 1
                if 22 <= gap <= 42:
                    s += 1
                scored.append({'parent': p['id'], 'child': c, 'gap': gap, 'score': s})
        if not scored:
            continue
        scored.sort(key=lambda x: -x['score'])
        best = scored[0]
        rivals = [x for x in scored if x['parent'] != best['parent']]
        unique = not rivals
        placed = compatible(by_id[best['parent']]['place'], h['place']) == 2
        good_gap = 20 <= best['gap'] <= 45
        if unique and placed and good_gap:
            conf = 'strong'          # one candidate, same parish, ordinary generation gap
        elif unique:
            conf = 'probable'        # one candidate, but the parish or the gap is not confirmed
        elif best['score'] - rivals[0]['score'] >= 2:
            conf = 'possible'
        else:
            ambiguous.append({'household': h['id'], 'options': [
                {'parent': x['parent'], 'via': x['child']['name'], 'gap': x['gap'], 'score': x['score']}
                for x in scored[:4]]})
            continue
        links.append({'child': h['id'], 'parent': best['parent'], 'via': best['child']['name'],
                      'viaId': best['child']['id'], 'gap': best['gap'], 'confidence': conf,
                      'score': best['score']})
    return links, ambiguous

def chains(hs, links):
    parent_of = {l['child']: l for l in links}
    kids = defaultdict(list)
    for l in links:
        kids[l['parent']].append(l['child'])
    roots = [h['id'] for h in hs if h['id'] not in parent_of and kids.get(h['id'])]
    by_id = {h['id']: h for h in hs}

    def depth(i):
        return 1 + max((depth(k) for k in kids.get(i, [])), default=0)

    out = []
    for r in roots:
        def walk(i):
            return {'id': i, 'household': by_id[i], 'link': parent_of.get(i),
                    'children': [walk(k) for k in kids[i]]}
        out.append({'root': r, 'generations': depth(r), 'tree': walk(r),
                    'size': 1 + sum(1 for _ in iter_ids(r, kids))})
    out.sort(key=lambda x: (-x['generations'], -x['size']))
    return out

def iter_ids(i, kids):
    for k in kids.get(i, []):
        yield k
        yield from iter_ids(k, kids)

if __name__ == '__main__':
    hs = json.load(open('site/src/data/households.json', encoding='utf-8'))
    links, amb = candidates(hs)
    ch = chains(hs, links)
    json.dump({'links': links, 'ambiguous': amb, 'lineages': ch},
              open('site/src/data/lineages.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    by_id = {h['id']: h for h in hs}
    print(f'{len(hs)} households -> {len(links)} generational links '
          f'({sum(1 for l in links if l["confidence"]=="strong")} strong, '
          f'{sum(1 for l in links if l["confidence"]=="probable")} probable, '
          f'{sum(1 for l in links if l["confidence"]=="possible")} possible), '
          f'{len(amb)} ambiguous, {len(ch)} lineages')
    for c in ch:
        h = by_id[c['root']]
        print(f"\n  {c['generations']} generations, {c['size']} households — root: "
              f"{h['father']} + {h['mother']} ({h['place']}, {h['from']})")
        def show(n, d=1):
            for k in n['children']:
                kh = k['household']; l = k['link']
                print(f"    {'  '*d}└─ via {l['via'][:38]:<38} gap {l['gap']:>2}y  {l['confidence']:<8} "
                      f"{kh['father'][:26]} + {kh['mother'][:20]} ({kh['from']})")
                show(k, d+1)
        show(c['tree'])
