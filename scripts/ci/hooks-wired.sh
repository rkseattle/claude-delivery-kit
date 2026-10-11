#!/usr/bin/env bash
# The hooks are wired, and every command hooks.json names exists and is executable.
# Usage: hooks-wired.sh [repo-root]
#
# A self-test passes whether or not anything still points at the hook, so this asserts the
# wiring itself: a hooks.json entry renamed, retyped, or pointed at a missing path.
set -euo pipefail
root="$(cd "${1:-.}" && pwd)"
jq -e '.hooks.Stop[0].hooks[0].command' "$root/hooks/hooks.json" > /dev/null
jq -e '.hooks.PostToolUse[] | select(.matcher == "Bash")' "$root/hooks/hooks.json" > /dev/null
cmds=$(jq -er '.hooks | to_entries[] | .value[] | .hooks[] | .command' "$root/hooks/hooks.json") \
  || { echo "hooks.json has an entry with no hooks[].command"; exit 1; }
fail=0
while IFS= read -r cmd; do
  path="${cmd/\$\{CLAUDE_PLUGIN_ROOT\}/$root}"
  if [ -x "$path" ]; then
    echo "ok: $path"
  else
    echo "hook command is not executable: $path"
    fail=1
  fi
done <<< "$cmds"
exit "$fail"
