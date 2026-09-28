#!/bin/bash
# Build and gate into a PRIVATE output directory.
#
# site/dist is shared ground: other Claude sessions on this machine build into
# this project's tree, and on 21 September 2026 three separate builds of mine
# died mid-run because a foreign build wiped or rewrote dist underneath them —
# "Cannot find module dist/pages/who.astro.mjs", and once checkarchive itself
# refused to report because "dist changed while this ran".
#
# So this gate never touches dist. It builds into site/dist-gate-$$ and points
# every dist-reading check at that, then removes it. A foreign build racing in
# dist cannot affect the result, and this gate cannot corrupt theirs either.
#
# Exit: 0 all gates green · 1 a gate failed · 2 the build itself failed
set -uo pipefail
cd "$(dirname "$0")/../site" || exit 2
OUT="dist-gate-$$"
KIT="node_modules/@daviddef/archive-kit/kit/tools"
cleanup() { rm -rf "$OUT"; }
trap cleanup EXIT

# THE OBJECT STORE FIRST, because a green build proves nothing about it.
# On 27 September this archive built 2,940 pages and passed twelve checks with
# 32 objects missing and 30 links broken. Every check in the suite read FILES;
# none read git. It costs 93ms, and if it fails there is no point building.
# NB: this runs AFTER the cd into site/, so the path is ../scripts, exactly as
# the other archive-owned checks below are invoked. $(dirname "$0") is relative
# to the ORIGINAL cwd and resolved to site/./scripts on the first attempt.
if ! python3 ../scripts/check-repo.py; then
  echo "gate: REPOSITORY DAMAGED — not building"; exit 2
fi

export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=2048}"
echo "gate: building into $OUT (dist left alone)"
npm run publish:index >/dev/null 2>&1 || { echo "gate: publish:index failed"; exit 2; }
npx astro build --outDir "$OUT" > "/tmp/gate-$$.log" 2>&1 || {
  echo "gate: BUILD FAILED"; tail -12 "/tmp/gate-$$.log"; exit 2; }
echo "gate: built $(grep -oE '[0-9]+ page\(s\) built' "/tmp/gate-$$.log" | tail -1)"

# The kit's sitemap generator hardcodes site/dist and takes no arguments, but it
# derives `site` from the CURRENT DIRECTORY. So give it a private one: a scratch
# tree whose `site/dist` is a symlink to our isolated build. It writes the
# sitemap where we want it and never sees the shared dist. Nothing in the kit is
# modified to achieve this — the kit is another session's surface.
SCRATCH="$(mktemp -d)"
mkdir -p "$SCRATCH/site"
cp astro.config.mjs "$SCRATCH/site/" 2>/dev/null
ln -s "$PWD/$OUT" "$SCRATCH/site/dist"
ln -s "$PWD/public" "$SCRATCH/site/public" 2>/dev/null
KITABS="$PWD/$KIT"
( cd "$SCRATCH/site" && python3 "$KITABS/sitemap.py" ) >/dev/null 2>&1 \
  && echo "  ok    sitemap (into $OUT)" || echo "  warn  sitemap generator did not run"
rm -rf "$SCRATCH"

fail=0
run() { # name, command...
  local n="$1"; shift
  local out; out="$("$@" 2>&1)"; local rc=$?
  if [ $rc -ne 0 ] || echo "$out" | grep -q "FAIL"; then
    echo "  FAIL  $n"; echo "$out" | grep -E "FAIL|→|->" | head -6; fail=1
  else
    echo "  ok    $n"
  fi
}
run living    ../scripts/kit-living.sh          --dist "$OUT" --data src/data --policy named-bare
run templates python3 "$KIT/checktemplates.py" --root .
run kit       python3 "$KIT/checkarchive.py"  --dist "$OUT"
run worklist  python3 "$KIT/checkworklist.py" --root .
run covers    python3 "$KIT/checkcovers.py"   --root .
run evidence  python3 ../scripts/check-evidence.py --dist "$OUT"
run names     python3 ../scripts/name-forms-audit.py --check
run places    python3 "$KIT/checkplaces.py"   --data public/atlas-data.json
run licences ../scripts/check-licences.py --dist "$OUT"
run livingdata ../scripts/check-living-data.py
run dates      ../scripts/check-dates-everywhere.py
# Last, and it reports on the others: every line above is a steady number
# restated identically each build, and a line beginning "ok" does not get read.
# This one speaks only when a number MOVES. See scripts/check-witness.py.
#
# NOT through run(). run() prints the check's own output only when it FAILS,
# so the witness wired through it was silent in exactly the case it exists
# for: a living count moving 99 -> 59 printed "ok witness" and nothing else.
# The gate was hiding the one line meant to be read, which is the fault the
# witness was written to catch, reproduced in the harness around it.
# Decisions before the witness: a decision changing is a refusal, a count
# moving is only news. Both run outside run() because run() prints a check's
# own output only on failure, and both of these have something to say while
# passing.
if ! ../scripts/check-decisions.py; then fail=1; fi
if ! ../scripts/check-witness.py; then fail=1; fi
# Propagation last of the three: a correction is not done when it is written,
# only when the old claim is gone from every file that asserts it. Added after
# a corrected name stayed live in households.json for five days and kept a
# child filed under the wrong household. See scripts/check-propagation.py.
if ! ../scripts/check-propagation.py; then fail=1; fi
# Story last, and it SPEAKS rather than blocks: it counts findings that never
# left the search log. Forty-four existed when it was written, so failing the
# gate on them would only teach people to stop running the gate. The number is
# printed on every build and should only ever go down. --strict to enforce.
../scripts/check-story.py | head -2
[ -f "$KIT/checkpages.py" ] && run pages python3 "$KIT/checkpages.py" --root . --estate ../.. --max-bespoke 9
[ $fail -eq 0 ] && echo "gate: ALL GREEN" || echo "gate: NOT GREEN"
exit $fail
