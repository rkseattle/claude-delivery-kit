#!/usr/bin/env bash
# deliver's line budget, enforced. Every run is asked for friction and no run is asked what
# to remove, so without this the corpus only ever grows. Usage: line-budget.sh [repo-root]
#
# A skill counts as its SKILL.md plus its references/, because a split that moved text out
# of sight of the budget would let the ratchet resume under a different name.
set -euo pipefail
root="${1:-.}"
fail=0
check() {
  local n
  n=$(wc -l < "$1" | tr -d ' ')
  if [ "$n" -gt "$2" ]; then echo "OVER CAP $1: $n > $2"; fail=1; fi
}
check_skill() {
  local dir n
  dir="$(dirname "$1")"
  # shellcheck disable=SC2046
  n=$(cat "$1" $(find "$dir/references" -name '*.md' 2>/dev/null | sort) | wc -l | tr -d ' ')
  if [ "$n" -gt "$2" ]; then
    echo "OVER CAP $1 (+references): $n > $2"; fail=1
  else
    echo "ok: $1 (+references) = $n <= $2"
  fi
}
for f in "$root"/skills/*/SKILL.md; do check_skill "$f" 480; done
for f in "$root"/agents/*.md; do check "$f" 140; done
for f in "$root"/gates/*.md; do
  if [ "$(basename "$f")" = "status-report.md" ]; then check "$f" 140; else check "$f" 300; fi
done
exit "$fail"
