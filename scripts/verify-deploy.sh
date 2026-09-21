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
      if [ "$CONC" = "cancelled" ]; then
        # GitHub cancels an in-flight run when a newer push lands. That is not a
        # failure of OUR commit: if a LATER run succeeded and our commit is an
        # ancestor of what it built, our work shipped inside somebody else's run.
        git fetch -q origin 2>/dev/null
        NEWER="$(gh run list --limit 20 --json headSha,status,conclusion,databaseId \
                 --jq '.[] | select(.status=="completed" and .conclusion=="success") | "\(.headSha)\t\(.databaseId)"' 2>/dev/null | head -5)"
        while IFS=$'\t' read -r NSHA NID; do
          [ -z "${NSHA:-}" ] && continue
          if git merge-base --is-ancestor "$SHA" "$NSHA" 2>/dev/null; then
            echo "verify-deploy: SUPERSEDED but SHIPPED  $SHORT  (carried by run $NID on ${NSHA:0:7})"; exit 0
          fi
        done <<< "$NEWER"
        echo "verify-deploy: run for $SHORT was cancelled and no later successful run carries it yet — waiting"
        sleep 20; WAITED=$((WAITED+20)); continue
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
