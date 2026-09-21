#!/bin/bash
# Did the thing we just pushed actually DEPLOY?
#
# publish.sh proves the build is good ON THIS LAPTOP. It cannot prove the
# deploy succeeded, and on 21 September 2026 the difference cost a day: five
# commits reported PUSHED while every GitHub Actions run failed on a gate whose
# tool existed only in a local node_modules. The local gate was green the whole
# time. Never again treat PUBLISH_EXIT=0 as "it is live".
#
# Usage:  scripts/verify-deploy.sh [timeout-seconds]
# Exit :  0 the run for HEAD succeeded · 1 it failed · 2 it never appeared
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
SHA="$(git rev-parse HEAD)"; SHORT="${SHA:0:7}"
LIMIT="${1:-420}"; WAITED=0
command -v gh >/dev/null || { echo "verify-deploy: gh not installed — cannot confirm the deploy"; exit 2; }

echo "verify-deploy: watching the run for $SHORT"
while [ "$WAITED" -lt "$LIMIT" ]; do
  LINE="$(gh run list --limit 20 --json headSha,status,conclusion,databaseId,displayTitle \
          --jq ".[] | select(.headSha==\"$SHA\") | \"\(.status)\t\(.conclusion)\t\(.databaseId)\"" 2>/dev/null | head -1)"
  if [ -n "$LINE" ]; then
    STATUS="$(echo "$LINE" | cut -f1)"; CONC="$(echo "$LINE" | cut -f2)"; ID="$(echo "$LINE" | cut -f3)"
    if [ "$STATUS" = "completed" ]; then
      if [ "$CONC" = "success" ]; then
        echo "verify-deploy: DEPLOYED  $SHORT  (run $ID)"; exit 0
      fi
      echo "verify-deploy: DEPLOY FAILED  $SHORT  (run $ID, $CONC)"
      echo "--- failing step ---"
      gh run view "$ID" --log-failed 2>/dev/null | grep -vE '^\s*$' | tail -12
      exit 1
    fi
  fi
  sleep 15; WAITED=$((WAITED+15))
done
echo "verify-deploy: no completed run for $SHORT after ${LIMIT}s — check manually"; exit 2
