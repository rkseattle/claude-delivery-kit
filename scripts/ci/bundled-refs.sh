#!/usr/bin/env bash
# Every ${CLAUDE_PLUGIN_ROOT} reference names a tracked file, or a directory holding one.
# These resolve at runtime inside a project, so a typo surfaces as a stage silently reading
# nothing rather than as an error. Whether git tracks a reference is project_rules' one
# rule, not a test on disk, so an untracked or wrongly cased file fails here as in CI.
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
gates="$(cd "$(dirname "$0")/../../gates/scripts" && pwd)"
references=()
while IFS= read -r ref; do references+=("$ref"); done <<< "$refs"
python3 - "$root" "$gates" "${references[@]}" <<'PY'
import sys
sys.dont_write_bytecode = True
root, gates, references = sys.argv[1], sys.argv[2], sys.argv[3:]
sys.path.insert(0, gates)
from project_rules import tracked_path_matcher  # noqa: E402
try:
    is_tracked = tracked_path_matcher(root)
except ValueError as error:
    sys.exit(str(error))
failed = False
for reference in references:
    if is_tracked(reference[len("${CLAUDE_PLUGIN_ROOT}/"):]):
        print(f"ok: {reference}")
    else:
        print(f"BROKEN: {reference}")
        failed = True
sys.exit(1 if failed else 0)
PY
