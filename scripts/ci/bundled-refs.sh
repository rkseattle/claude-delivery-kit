#!/usr/bin/env bash
# Every ${CLAUDE_PLUGIN_ROOT} reference names a file that exists. These resolve at runtime
# inside a project, so a typo surfaces as a stage silently reading nothing rather than as
# an error. Usage: bundled-refs.sh [repo-root]
#
# A here-string, not `grep | while read`: a pipe runs the loop in a subshell, so neither
# the flag nor an `exit` inside it reaches the script and the check always passes. A failed
# or empty scan fails too, rather than reading as no broken references.
set -euo pipefail
root="${1:-.}"
refs=$(cd "$root" && grep -rhoE '\$\{CLAUDE_PLUGIN_ROOT\}/[a-zA-Z0-9/_.-]+' skills gates agents | sort -u) \
  || { echo "cannot scan skills, gates and agents under $root"; exit 1; }
fail=0
while read -r ref; do
  p="$root${ref#\$\{CLAUDE_PLUGIN_ROOT\}}"
  if [ -e "$p" ]; then echo "ok: $ref"; else echo "BROKEN: $ref"; fail=1; fi
done <<< "$refs"
exit "$fail"
