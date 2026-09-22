#!/bin/bash
# Run the kit's checkliving.py, working around a bug in the INSTALLED kit
# without touching node_modules, which is shared ground.
#
# The kit added an in-flight-build guard to checkliving.py and the two halves of
# the edit landed in the wrong places: `_before = _outdir.fingerprint(a.dist)`
# sits inside feed(), which has no `a`, and main() calls
# `_outdir.settled(a.dist, _before, 'living')` with `_before` never assigned.
# main() therefore raises NameError at line 489 — BEFORE it calls report(), so
# the run produces no verdict at all. Every archive on this machine using this
# kit build has a living gate that cannot pass or fail.
#
# This script copies the tool to the session scratchpad, moves that one line to
# where it was meant to go, and runs the copy. It changes nothing in the kit and
# nothing in the repository; if the installed kit is healthy it runs it directly.
set -uo pipefail
KIT="$(dirname "$0")/../site/node_modules/@daviddef/archive-kit/kit/tools"
TOOL="$KIT/checkliving.py"
if ! grep -q "^    _before = _outdir.fingerprint(a.dist)$" "$TOOL" 2>/dev/null \
   || ! awk 'NR>=363 && NR<=390' "$TOOL" | grep -q "_before = _outdir.fingerprint"; then
  exec python3 "$TOOL" "$@"          # healthy, or changed shape — use it as-is
fi
S="${TMPDIR:-/tmp}/kit-living-$$"; mkdir -p "$S"; trap 'rm -rf "$S"' EXIT
cp "$KIT"/*.py "$S/"
python3 - "$S/checkliving.py" <<'PY'
import sys, io
p = sys.argv[1]; s = io.open(p, encoding="utf-8").read()
s = s.replace("    _before = _outdir.fingerprint(a.dist)\n    pages = load_pages(dist)\n",
              "    pages = load_pages(dist)\n", 1)
s = s.replace("    a.dist = _outdir.resolve(a.dist)\n    today = datetime.date.today()\n",
              "    a.dist = _outdir.resolve(a.dist)\n"
              "    _before = _outdir.fingerprint(a.dist)\n"
              "    today = datetime.date.today()\n", 1)
io.open(p, "w", encoding="utf-8").write(s)
PY
echo "  note  installed checkliving.py raises NameError before reporting; ran a repaired private copy (kit untouched)" >&2
exec python3 "$S/checkliving.py" "$@"
