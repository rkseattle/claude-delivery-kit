#!/usr/bin/env bash
# Every ${CLAUDE_PLUGIN_ROOT} reference names a tracked file, or a directory holding one.
# These resolve at runtime inside a project, so a typo surfaces as a stage silently reading
# nothing rather than as an error. A reference is matched against `git ls-files` exactly,
# not tested on disk, so an untracked or wrongly cased file fails here as in CI.
# Usage: bundled-refs.sh [repo-root]
#
# A here-string, not `grep | while read`: a pipe runs the loop in a subshell, so neither
# the flag nor an `exit` inside it reaches the script and the check always passes. A failed
# or empty scan fails too, rather than reading as no broken references.
set -euo pipefail
# The pattern is ASCII; matching bytes keeps a stray invalid UTF-8 byte from hiding a line.
export LC_ALL=C
root="${1:-.}"
refs=$(cd "$root" && grep -rhoaE '\$\{CLAUDE_PLUGIN_ROOT\}/[a-zA-Z0-9/_.-]+' skills gates agents | sort -u) \
  || { echo "cannot scan skills, gates and agents under $root"; exit 1; }
tracked=$(git -C "$root" -c core.quotePath=false ls-files) \
  || { echo "cannot list the tracked files under $root"; exit 1; }
fail=0
while read -r ref; do
  p="${ref#\$\{CLAUDE_PLUGIN_ROOT\}/}"
  if grep -qxF -- "$p" <<< "$tracked" \
     || awk -v dir="${p%/}/" 'index($0, dir) == 1 { found = 1; exit } END { exit !found }' <<< "$tracked"; then
    echo "ok: $ref"
  else
    echo "BROKEN: $ref"; fail=1
  fi
done <<< "$refs"
exit "$fail"
