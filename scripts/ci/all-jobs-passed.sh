#!/usr/bin/env bash
# The single check to require in branch protection. In CI it reads the needs context
# (NEEDS, set from `toJSON(needs)`) and fails when any job it waits on failed or was
# cancelled, or is missing from the results. A skipped job passes, per gates/pre-push.md's
# rule for an aggregating check, so a future path filter cannot turn every PR red. Everywhere it also checks ci.yml's own wiring: the job must
# need every other job and run `if: always()`, because a required check that is skipped
# when a dependency fails reports as passing. Usage: all-jobs-passed.sh [repo-root]
set -euo pipefail
root="${1:-.}"
ci="$root/.github/workflows/ci.yml"
self="ci-passed"

jobs=$(awk '/^jobs:/ { in_jobs = 1; next } in_jobs && /^[^ #]/ { in_jobs = 0 }
            in_jobs && /^  [A-Za-z0-9_-]+:[[:space:]]*(#.*)?$/ { sub(/^  /, ""); sub(/:.*/, ""); print }' "$ci")
[ -n "$jobs" ] || { echo "no jobs found in $ci"; exit 1; }
grep -qx "$self" <<< "$jobs" || { echo "ci.yml has no $self job"; exit 1; }

block=$(awk -v job="  $self:" '$0 == job { on = 1; next } on && /^  [^ ]/ { on = 0 } on' "$ci")
grep -qE '^    if: always\(\)$' <<< "$block" || { echo "$self must run with if: always()"; exit 1; }
needs=$(sed -n 's/^    needs: \[\(.*\)\]$/\1/p' <<< "$block" | tr -d ' ' | tr ',' '\n' | sort)
others=$(grep -vx "$self" <<< "$jobs" | sort)
if [ "$needs" != "$others" ]; then
  echo "$self needs [$(tr '\n' ' ' <<< "$needs")], but the other jobs are [$(tr '\n' ' ' <<< "$others")]"
  exit 1
fi

if [ -z "${NEEDS:-}" ]; then
  echo "ok: $self needs every job and runs if: always() (no CI results outside CI)"
  exit 0
fi
jq -e 'type == "object" and length > 0' <<< "$NEEDS" > /dev/null 2>&1 \
  || { echo "NEEDS is not a job-results object"; exit 1; }
reported=$(jq -r 'keys[]' <<< "$NEEDS" | sort)
if [ "$reported" != "$needs" ]; then
  echo "job results cover [$(tr '\n' ' ' <<< "$reported")], not [$(tr '\n' ' ' <<< "$needs")]"
  exit 1
fi
failed=$(jq -r 'to_entries[] | select(.value.result | IN("success", "skipped") | not)
                | "\(.key): \(.value.result)"' <<< "$NEEDS")
if [ -n "$failed" ]; then
  echo "jobs that did not succeed:"; echo "$failed"; exit 1
fi
echo "ok: every job succeeded"
