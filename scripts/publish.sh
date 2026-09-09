#!/usr/bin/env bash
# Build, verify, relink, commit, push — and REFUSE to push a broken build.
#
# Twice now a broken site has been pushed because `npm run build | tail -2`
# hides the build's exit code behind the pipe's. This script does not pipe.
#
#   ./scripts/publish.sh "commit subject" "body line" ["body line" ...]
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/build-search-index.py

if ! npm --prefix site run build > /tmp/defr-build.log 2>&1; then
  echo "BUILD FAILED — nothing committed, nothing pushed."
  tail -25 /tmp/defr-build.log
  exit 1
fi
tail -2 /tmp/defr-build.log

# every page that exists in src must exist in dist
missing=0
while IFS= read -r page; do
  slug="${page#site/src/pages/}"; slug="${slug%.astro}"
  [[ "$slug" == *"["* ]] && continue
  slug="${slug%/index}"; [[ "$slug" == "index" ]] && slug=""
  [[ -z "$slug" ]] && out="site/dist/index.html" || out="site/dist/$slug/index.html"
  [[ -f "$out" ]] || { echo "MISSING OUTPUT: /$slug/"; missing=1; }
done < <(find site/src/pages -name '*.astro')
[[ $missing -eq 0 ]] || { echo "Pages missing from dist — nothing pushed."; exit 1; }

( cd site/dist && ln -sfn . TheDefranceski )

subject="$1"; shift
git add -A
if git diff --cached --quiet; then echo "Nothing to commit."; exit 0; fi
{ printf '%s\n' "$subject"; for l in "$@"; do printf '\n%s\n' "$l"; done;
  printf '\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n'; } | git commit -q -F -
git push -q origin main
echo "PUSHED: $(git log --oneline -1)"
