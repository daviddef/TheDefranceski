#!/usr/bin/env python3
"""Fill the template with a tree and an Atlas slice and write the page.

    build_page.py --tree build/tree.json --atlas-data build/atlas-data.json --out site/public/roots/index.html \
        [--title "Roots & Routes"] [--subtitle "..."] [--atlas-url https://recordatlas.org] [--back-url / --back-label "The Archive"]

The page is one self-contained HTML file: no network calls except links the reader clicks.
"""
import argparse, json, os, re, html
VERSION = '1.1.0'
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', default=os.path.join(os.path.dirname(__file__), '..', 'assets', 'tree-views.template.html'))
    ap.add_argument('--tree', required=True); ap.add_argument('--atlas-data', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--title'); ap.add_argument('--subtitle'); ap.add_argument('--atlas-url', default='https://recordatlas.org')
    ap.add_argument('--back-url'); ap.add_argument('--back-label', default='Back to the archive')
    ap.add_argument('--check', action='store_true', help='only report whether the existing page was built from an older template')
    a = ap.parse_args()
    if a.check:
        old = open(a.out).read() if os.path.exists(a.out) else ''
        m = re.search(r'name="family-tree-page" content="([^"]+)"', old)
        print('page template: %s, skill template: %s' % (m.group(1) if m else 'none', VERSION)); return
    t = open(a.template, encoding='utf-8').read()
    tree = json.load(open(a.tree)); at = open(a.atlas_data, encoding='utf-8').read()
    if a.title: tree.setdefault('meta', {})['title'] = a.title
    if a.subtitle: tree.setdefault('meta', {})['sub'] = a.subtitle
    for ph in ('/*ATLAS_DATA*/null', '/*TREE_DATA*/null'):
        assert ph in t, 'template is missing ' + ph
    t = t.replace('/*ATLAS_DATA*/null', at).replace('/*TREE_DATA*/null', json.dumps(tree, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    t = t.replace('https://recordatlas.org', a.atlas_url.rstrip('/'))
    title = (tree.get('meta') or {}).get('title') or 'Roots & Routes'
    t = re.sub(r'<title>.*?</title>', '<title>' + html.escape(title, quote=False) + '</title>\n<meta name="family-tree-page" content="' + VERSION + '">', t, count=1)
    if a.back_url:
        t = t.replace('<div class="wrap">', '<div class="wrap">\n  <p style="margin:0 0 10px;font-size:13px"><a href="' + html.escape(a.back_url) + '">← ' + html.escape(a.back_label) + '</a></p>', 1)
    if not t.lstrip().lower().startswith('<!doctype'):   # a standards-mode document with the base rules the template relies on
        t = ('<!doctype html>\n<html lang="en">\n<head>\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
             '<style>[hidden]{display:none!important}body{margin:0}img{max-width:100%}</style>\n' + t + '\n</body>\n</html>\n')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write(t)
    print('wrote %s (%.0f KB)' % (a.out, len(t.encode()) / 1024))
if __name__ == '__main__': main()
