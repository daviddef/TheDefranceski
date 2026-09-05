"""Import a GEDCOM into the archive's data model, applying the living-person rule."""
import json, re, sys, datetime

def parse(path):
    inds, fams, cur, tag = {}, {}, None, None
    for raw in open(path, encoding='utf-8', errors='replace'):
        line = raw.rstrip('\n')
        m = re.match(r'^(\d+) (@[^@]+@ )?(\w+)( (.*))?$', line)
        if not m:
            if cur is not None and line.startswith('2 CONT'):
                cur.setdefault('_note', []).append(line[7:])
            continue
        lvl, xref, t, _, val = m.groups()
        lvl = int(lvl)
        if lvl == 0:
            if t == 'INDI':
                cur = inds.setdefault(xref.strip(), {'id': xref.strip(), 'fams': [], 'famc': []})
            elif t == 'FAM':
                cur = fams.setdefault(xref.strip(), {'id': xref.strip(), 'chil': []})
            else:
                cur = None
            tag = None
        elif cur is not None:
            if lvl == 1:
                tag = t
                if t == 'NAME': cur['name'] = (val or '').replace('/', '').strip()
                elif t == 'SEX': cur['sex'] = val
                elif t == 'NPFX': cur['npfx'] = val
                elif t in ('FAMS',): cur['fams'].append(val)
                elif t in ('FAMC',): cur['famc'].append(val)
                elif t in ('HUSB','WIFE'): cur[t.lower()] = val
                elif t == 'CHIL': cur['chil'].append(val)
                elif t == 'NOTE': cur.setdefault('notes', []).append(val or '')
                elif t in ('BIRT','DEAT','MARR','BURI','CHR'): cur.setdefault('_ev', {}).setdefault(t, {})
            elif lvl == 2 and tag in ('BIRT','DEAT','MARR','BURI','CHR'):
                if t == 'DATE': cur['_ev'][tag]['date'] = val
                elif t == 'PLAC': cur['_ev'][tag]['place'] = val
                elif t == 'NOTE': cur['_ev'][tag]['note'] = val
            elif lvl == 2 and t == 'SURN': cur['surn'] = val
            elif lvl == 2 and t == 'GIVN': cur['givn'] = val
            elif lvl == 2 and t == 'NPFX': cur['npfx'] = val
    return inds, fams

def year(d):
    m = re.search(r'\b(1[5-9]\d\d|20\d\d)\b', d or '')
    return int(m.group(1)) if m else None

if __name__ == '__main__':
    src = sys.argv[1]
    inds, fams = parse(src)
    THIS_YEAR = datetime.date.today().year
    people, omitted = [], 0
    for i in inds.values():
        ev = i.get('_ev', {})
        b = year(ev.get('BIRT', {}).get('date'))
        d = year(ev.get('DEAT', {}).get('date'))
        # living-person rule: omit anyone with no death date who could plausibly be alive
        if not d and b and (THIS_YEAR - b) < 105:
            omitted += 1
            continue
        if not d and not b:
            pass
        people.append({
            'gid': i['id'], 'name': i.get('name', ''), 'sex': i.get('sex', ''),
            'title': i.get('npfx', ''),
            'birth': ev.get('BIRT', {}).get('date', ''), 'birthYear': b,
            'death': ev.get('DEAT', {}).get('date', ''), 'deathYear': d,
            'place': ev.get('BIRT', {}).get('place', '') or ev.get('DEAT', {}).get('place', ''),
            'notes': [n for n in i.get('notes', []) if n][:3],
            'famc': i.get('famc', []), 'fams': i.get('fams', []),
        })
    famlist = []
    for f in fams.values():
        ev = f.get('_ev', {})
        famlist.append({'gid': f['id'], 'husb': f.get('husb'), 'wife': f.get('wife'),
                        'chil': f.get('chil', []),
                        'marriage': ev.get('MARR', {}).get('date', ''),
                        'marriagePlace': ev.get('MARR', {}).get('place', '')})
    out = {'source': src.split('/')[-1], 'people': people, 'families': famlist,
           'omittedLiving': omitted, 'counts': {'individuals': len(inds), 'families': len(fams)}}
    json.dump(out, open('site/src/data/gologorica.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{len(inds)} individuals, {len(fams)} families -> published {len(people)}, omitted {omitted} possibly living")
    yrs = [p['birthYear'] for p in people if p['birthYear']]
    print(f"birth years {min(yrs)}–{max(yrs)}")
