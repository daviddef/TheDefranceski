#!/usr/bin/env bash
# whoelse.sh — has a SIBLING archive already done this?
#
# Why this exists. On 29 September 2026 this archive published a "first step"
# on the parish of Brinje — are its registers filmed? — and the answer had been
# established a fortnight earlier by the Blazevic archive, which had located
# both films, measured that nothing is indexed, and was reading the marriage
# book that same day. Nothing caught it. David did.
#
# Three repeats earlier the same day were caught by grepping THIS archive's own
# logs, which the working rules already require. This one was invisible to that
# check because the work was in another repository. The rule generalises: the
# estate is one body of research kept in several trees, and a question answered
# in any of them is answered.
#
#   ./scripts/whoelse.sh Brinje
#   ./scripts/whoelse.sh Kalanj Perkovic
#
# It greps every sibling archive's data for each term and prints which files
# mention it and how often. Deliberately dumb: it reports, it does not judge.
# A hit means GO AND READ THAT FILE before claiming a discovery.
#
# TWO BUGS WERE WRITTEN INTO THIS FILE BEFORE IT WORKED, both worth the comment.
# The estate is not flat — this archive is at ~/Projects/<name> while the others
# are at ~/Projects/Family Projects/<name> — and every one of those paths has a
# SPACE in it, so `for d in $(...)` split "Defranceski Family" into two and the
# script reported a confident "no sibling archive mentions it" for a term that
# four Blazevic files carry. A checker that lies in the reassuring direction is
# worse than no checker.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MINE="$(basename "$ROOT")"
PARENT="$(cd "$ROOT/.." && pwd)"

if [ "$#" -eq 0 ]; then
  echo "usage: ./scripts/whoelse.sh <term> [term...]" >&2
  exit 2
fi

# Collect candidate archive directories, NUL-separated so spaces survive.
collect() {
  find "$PARENT" -maxdepth 1 -mindepth 1 -type d -print0 2>/dev/null
  if [ -d "$PARENT/Family Projects" ]; then
    find "$PARENT/Family Projects" -maxdepth 1 -mindepth 1 -type d -print0 2>/dev/null
  fi
}

found_any=0
for term in "$@"; do
  echo "=== \"$term\""
  hits=0
  while IFS= read -r -d '' dir; do
    name="$(basename "$dir")"
    [ "$name" = "$MINE" ] && continue
    case "$name" in _*) continue ;; esac
    [ -d "$dir/site/src/data" ] || continue

    counts="$(grep -ric -- "$term" "$dir/site/src/data/"*.json 2>/dev/null \
              | awk -F: '$NF > 0 {n += $NF; f++} END {if (f) print n" "f}')"
    [ -z "$counts" ] && continue

    n="${counts%% *}"; f="${counts##* }"
    printf '  %-26s %s mention(s) in %s file(s)\n' "$name" "$n" "$f"
    grep -ril -- "$term" "$dir/site/src/data/"*.json 2>/dev/null \
      | while IFS= read -r hit; do printf '      %s\n' "$(basename "$hit")"; done | head -6
    hits=$((hits + 1)); found_any=1
  done < <(collect)

  [ "$hits" -eq 0 ] && echo "  no sibling archive mentions it"
  echo
done

if [ "$found_any" -eq 1 ]; then
  echo "A hit is not a verdict. Read those files before calling anything a discovery."
  echo "Verification is worth publishing; it is not discovery."
fi
exit 0
