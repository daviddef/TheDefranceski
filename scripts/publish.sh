#!/usr/bin/env bash
# Build, verify, relink, commit, push — and REFUSE to push a broken build.
#
# Twice now a broken site has been pushed because `npm run build | tail -2`
# hides the build's exit code behind the pipe's. This script does not pipe.
#
#   ./scripts/publish.sh "commit subject" "body line" ["body line" ...]
set -euo pipefail
cd "$(dirname "$0")/.."

# ALWAYS say how we ended. Adopted 21 Sept 2026 from the D'Arcy session, after
# an afternoon in which three publishes were each misdiagnosed:
#   - two died silently because they were launched `nohup ... &` inside a tool
#     call and were reaped with the calling shell;
#   - one did not die at all. It was piped through `tail -12` from OUTSIDE this
#     script, which buffers until the pipeline ends, so a healthy ten-minute
#     gate chain looked like a vanished process with an empty log. It was
#     declared dead, relaunched, and had already pushed.
# Note the header above: this script refuses to pipe its own build for exactly
# that reason, and the mistake was then made one level up.
#
# A SIGTERM'd build inside a gate chain also exits non-zero AFTER earlier gates
# have printed `ok`, so a killed run reads like a data fault. One line fixes
# all of it: the last line of the log now always states the exit status.
trap 'rc=$?; if [ "$rc" -eq 0 ]; then echo "PUBLISH_EXIT=0"; \
  else echo "PUBLISH_EXIT=$rc  (128+n means a signal: 143=TERM, 137=KILL)"; fi' EXIT

# The dist/TheDefranceski self-symlink (recreated at the end of every publish so
# the local preview serves the base path) makes Astro's own build recurse into
# itself and fail with a module-resolution error. Remove it before building.
# This has broken a publish four times; it is not going to be remembered by hand.
rm -f site/dist/TheDefranceski

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
  # Astro emits 404.astro as dist/404.html, not dist/404/index.html. Accept both
  # spellings rather than block every publish on a page that is present.
  [[ -f "$out" || -f "site/dist/$slug.html" ]] || { echo "MISSING OUTPUT: /$slug/"; missing=1; }
done < <(find site/src/pages -name '*.astro')
[[ $missing -eq 0 ]] || { echo "Pages missing from dist — nothing pushed."; exit 1; }

# standing audit — the numbers the notes quote, recomputed every publish
if [[ -f scripts/audit.py ]]; then
  python3 scripts/audit.py --md > notes/AUDIT.md || { echo "audit.py failed — nothing pushed."; exit 1; }
  echo "audit: $(sed -n '3p' notes/AUDIT.md)"
fi

# every row in the list data must actually reach its page — see /corrections/,
# 13 Sept 2026, when the Search Register was found drawing 112 of 197 rows
if [[ -f scripts/verify-rendered.py ]]; then
  python3 scripts/verify-rendered.py | tail -n 3
fi

( cd site/dist && ln -sfn . TheDefranceski )

subject="$1"; shift
git add -A
if git diff --cached --quiet; then echo "Nothing to commit."; exit 0; fi
{ printf '%s\n' "$subject"; for l in "$@"; do printf '\n%s\n' "$l"; done;
  printf '\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n'; } | git commit -q -F -
git push -q origin main
echo "PUSHED: $(git log --oneline -1)"
