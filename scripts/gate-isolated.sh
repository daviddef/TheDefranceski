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
# The living-people standard v2 (16 October 2026). It decides who is living ITSELF, from the committed roster and
# the built pages, and (with David's tree, which is outside the repository) from the tree; the generator's word
# is not taken. --require-tree: on this machine the tree must be found, or the people the rule holds out cannot
# be checked and the gate must say so rather than pass. CI has no tree and runs the same file without that flag
# (npm run check:living-v2). The second line plants 26 faults in a made-up archive and requires every one caught.
run livingv2  python3 ../scripts/check-living-v2.py --dist "$OUT" --require-tree
run livingv2-faults python3 ../scripts/test-living-v2.py
# Whose readers is this archive counting? Reads the BUILT html and picks the archive by
# ORIGIN. Written by the D'Arcy session on 12 October 2026, after Lerena, D'Arcy and Blazevic
# logged hours of pageviews to THIS archive's counter: base became "" for every archive
# that moved and find(a => a.base === base) returns the first, which is this one.
run counter   env ARCHIVE_OUT="$OUT" python3 ../scripts/check_counter.py
run templates python3 "$KIT/checktemplates.py" --root .
run kit       python3 "$KIT/checkarchive.py"  --dist "$OUT"
[ -f "$KIT/checknav.py" ] && run nav python3 "$KIT/checknav.py" --dist "$OUT" --strict
run worklist  python3 "$KIT/checkworklist.py" --root .
run covers    python3 "$KIT/checkcovers.py"   --root .
run evidence  python3 ../scripts/check-evidence.py --dist "$OUT"
run names     python3 ../scripts/name-forms-audit.py --check
run places    python3 "$KIT/checkplaces.py"   --data public/atlas-data.json
run licences ../scripts/check-licences.py --dist "$OUT"
run livingdata ../scripts/check-living-data.py
run dates      ../scripts/check-dates-everywhere.py
run golotoc    python3 ../scripts/check-golo-toc.py
run atlasout   python3 ../scripts/check-atlas-outcomes.py
run leads      python3 ../scripts/check-leads.py
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
# Addresses: the blind twin of check-links. A rename updates every inbound
# reference, so the old address has no link left to follow and the build is
# internally consistent while a published page 404s. This reads GIT HISTORY
# instead and requires every slug that ever built to still build or be named in
# the redirect table. Incremental against data/published-addresses.json, so it
# costs a third of a second. Found 12 October 2026: six addresses stranded, one
# of them for three weeks. See scripts/check-addresses.py.
if ! ../scripts/check-addresses.py; then fail=1; fi
# Absence next, and it is propagation's blind twin. check-propagation reads
# site/src/data/*.json; on 30 September the stale claim was a hardcoded
# fallback string in two .astro templates, so it was invisible to every check
# in this gate — the link checkers all passed, because the missing link was
# exactly what the sentence asserted. Runs against the BUILT site, which is
# why it sits here and not with the data checks, and takes THIS gate's build
# rather than site/dist, which may be older than what is being gated.
if ! ../scripts/check-absence.py --dist "site/$OUT"; then fail=1; fi
# Story last, and it SPEAKS rather than blocks: it counts findings that never
# left the search log. Forty-four existed when it was written, so failing the
# gate on them would only teach people to stop running the gate. The number is
# printed on every build and should only ever go down. --strict to enforce.
../scripts/check-story.py | head -2
# Coverage SPEAKS too, and for the same reason. On 30 September David asked
# whether the registers already opened had been finished; nobody could say,
# because it had never been counted. It was 4.0%. A coverage figure that is
# felt is always higher than one that is counted, so it is printed on every
# build. See scripts/check-coverage.py.
../scripts/check-coverage.py | tail -4
# And the walked check, which is coverage's sharper edge. On 1 October three
# rows claimed a WALK over sixty frames of the baptism book; twenty-seven had
# been opened. `walked` is the one field that tells the next person a book is
# FINISHED, so a sampled book marked walked is worse than an unread one.
# SPEAKS, because a page read and found empty leaves no citation behind it.
../scripts/check-walked.py | head -12
# ESTATE: checkpages compares this archive's pages with its siblings', and «fewer than two
# archives found» is «cannot run», which it reports with exit 0. From site/, ../.. is ~/Projects,
# one level ABOVE the siblings (they live in ~/Projects/Family Projects, where this checkout is
# a symlink), so this check printed «not run» and passed on every build until the 14 October
# fault sweep noticed. It is told where the estate is when it exists; where it does not (a CI
# runner, one repository) «not run» is the honest answer. --max-bespoke 0 is what package.json
# already asked for — the 9 here was looser than the build it stands in for.
ESTATE="../../Family Projects"; [ -d "$ESTATE" ] || ESTATE="../.."
[ -f "$KIT/checkpages.py" ] && run pages python3 "$KIT/checkpages.py" --root . --estate "$ESTATE" --max-bespoke 0
# The checks package.json's build runs and this gate did not. A gate that stands in for the
# build has to run what the build runs, or green here means less than green there.
# sources: no ratchet means it can only fail when the list is missing — ten sources have no way to
# be reached today, and the 11th must not slip in.
run sources python3 "$KIT/checksources.py" --root . --dist "$OUT" --max-unreachable 10
run inline  python3 "$KIT/checkinline.py"  --root . --max-inline 2
run rows    python3 "$KIT/checkrows.py"    --root .
run kin     python3 "$KIT/checkkin.py"     --data src/data/roster.json --born b --died d --max 0
run pin     python3 "$KIT/checkpin.py"     --root .
[ $fail -eq 0 ] && echo "gate: ALL GREEN" || echo "gate: NOT GREEN"
exit $fail
