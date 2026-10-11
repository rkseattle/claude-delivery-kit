#!/usr/bin/env bash
# Every CI step's command appears, in CI's order, in scripts/ci/all.sh, and appears in the
# pre-push mechanics file project.json names. A step added to CI cannot then leave the
# local equivalent silently short of it. Usage: ci-steps-mirrored.sh [repo-root]
set -euo pipefail
root="${1:-.}"
gate=$(jq -er '.mechanics_gate_pre_push' "$root/.claude/project.json") \
  || { echo "project.json names no mechanics_gate_pre_push"; exit 1; }
[ "$gate" != none ] && [ -f "$root/$gate" ] \
  || { echo "mechanics_gate_pre_push is $gate, not a file this repo has"; exit 1; }
mechanics="$root/$gate"
ci="$root/.github/workflows/ci.yml"
# A step with no run: line (an action) has no local command to mirror; only checkout may.
unmirrored=$(awk '
  function flush() { if (name != "" && !run && !checkout) print name; name = "" }
  /^ *- /                          { flush(); name = $0; run = 0; checkout = 0 }
  /^  [a-z]/                       { flush() }
  /^ *(- )?run: /                  { run = 1 }
  /^ *(- )?uses: actions\/checkout@/ { checkout = 1 }
  END                              { flush() }' "$ci")
[ -z "$unmirrored" ] || { echo "CI steps with no local command: $unmirrored"; exit 1; }
steps=$(sed -n 's/^ *run: //p' "$ci" | awk '!seen[$0]++')
[ -n "$steps" ] || { echo "no run: steps found in ci.yml"; exit 1; }
! grep -qxE '[|>][-+]?' <<< "$steps" \
  || { echo "a multi-line run: block has no single command to mirror; move it to scripts/ci/"; exit 1; }
fail=0
while IFS= read -r cmd; do
  grep -qxF "$cmd" "$root/scripts/ci/all.sh" || { echo "all.sh lacks: $cmd"; fail=1; }
  grep -E '^\|' "$mechanics" | grep -qF "| \`$cmd\` |" \
    || { echo "$mechanics has no table row for: $cmd"; fail=1; }
done <<< "$steps"
local_order=$(grep -xF -f <(printf '%s\n' "$steps") "$root/scripts/ci/all.sh" || true)
if [ "$fail" = 0 ] && [ "$local_order" != "$steps" ]; then
  echo "all.sh runs CI's steps in a different order"; fail=1
fi
[ "$fail" = 0 ] && echo "ok: every CI step is mirrored in all.sh and $mechanics"
exit "$fail"
