#!/usr/bin/env bash
# Wait for a publish log to finish, then SHOW ENOUGH OF IT.
#
#   ./scripts/wait-publish.sh /path/to/publish.log
#
# WHY THIS EXISTS. Every misdiagnosis on 21 September 2026 came from a wrapper
# that summarised, not from a tool that failed:
#
#   · `publish.sh ... | tail -12` — tail buffers until the pipeline ends, so a
#     healthy ten-minute build looked like a dead process with an empty log.
#     It was declared dead and relaunched; it had already pushed.
#   · `nohup publish.sh ... &` inside a tool call — reaped with the calling
#     shell, silently, log stuck at 53 bytes.
#   · `tail -5` on a failure — the last five lines are the trap and the exit
#     code, not the gate's own complaint about the data.
#
# The Blazevic session put the general form best, having been bitten twice by
# it in one day: A WRAPPER THAT SUMMARISES A FAILURE IS A SECOND PLACE FOR THE
# FAILURE TO HIDE. Their retry loop grepped for '^  FAIL ' and foundcheck
# refuses in prose, so four failed builds showed them nothing at all. The fix
# is not a better regex — it is to print the log unconditionally on a non-zero
# exit and let the gate speak for itself.
#
# So: quiet on success, loud on failure. Never a regex.
set -u
LOG="${1:?usage: wait-publish.sh <logfile>}"
while ! grep -q 'PUBLISH_EXIT=' "$LOG" 2>/dev/null; do sleep 15; done
line="$(grep -m1 'PUBLISH_EXIT=' "$LOG")"
rc="${line#PUBLISH_EXIT=}"; rc="${rc%% *}"
if [ "$rc" = "0" ]; then
  grep -m1 '^PUSHED:' "$LOG" || echo "$line"
else
  echo "=============== PUBLISH FAILED: $line"
  echo "=============== full tail follows; do not go hunting in the data until you have read it"
  tail -80 "$LOG"
fi
