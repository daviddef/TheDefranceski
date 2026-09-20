#!/usr/bin/env bash
# Kill ONLY this archive's astro build.
#
# WHY THIS EXISTS. Until 21 September 2026 this session ran
#     pkill -f "astro build"
# before every publish. `pkill -f` matches the full command line of EVERY
# process on the machine, and every archive on this Mac builds with
# `astro build` — so that one line reaped the Blazevic, D'arcy and Lerena
# builds too. The Lerena session traced three dead `verify.sh` runs to it
# and told us. At least one of our own publishes died the same way, exit 144,
# and was misread as a build fault of ours.
#
# The damage is worse than a wasted build: a SIGTERM'd `npm run build` in a
# gate chain exits non-zero AFTER several checks have printed `ok`, so it
# surfaces as an unexplained EXIT=1 with a clean-looking log.
#
# Match on the project path, never on the bare command.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAT="${ROOT}/site/node_modules/.bin/astro"

PIDS="$(pgrep -f "$PAT" 2>/dev/null | tr '\n' ' ')"
if [ -z "${PIDS// /}" ]; then
  echo "stop-my-build: nothing of ours running"
  exit 0
fi
echo "stop-my-build: killing$( echo " $PIDS" ) under $ROOT"
kill $PIDS 2>/dev/null || true
sleep 2
kill -9 $PIDS 2>/dev/null || true
exit 0
