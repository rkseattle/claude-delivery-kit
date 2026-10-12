#!/usr/bin/env bash
# deliver's line budget, enforced. Every run is asked for friction and no run is asked what
# to remove, so without this the corpus only ever grows. Usage: line-budget.sh [repo-root]
#
# A skill counts as its SKILL.md plus its references/, because a split that moved text out
# of sight of the budget would let the ratchet resume under a different name.
#
# Every cap is read from the table under "## The line budget" in deliver's invariants
# reference, the one place caps are defined. A row that is missing, repeated, or not a
# whole number fails as UNPARSEABLE cap table rather than falling back to a number here.
# The table's CLAUDE.md row governs consuming projects; the kit ships no CLAUDE.md to check.
set -euo pipefail
root="${1:-.}"
shopt -s nullglob
skills=("$root"/skills/*/SKILL.md)
[ "${#skills[@]}" -gt 0 ] || { echo "no skills/*/SKILL.md under $root"; exit 1; }
table="$root/skills/deliver/references/invariants.md"
[ -f "$table" ] || { echo "UNPARSEABLE cap table $table: no such file" >&2; exit 1; }
read_cap() {  # read_cap <label prefix>: the cap on the one row whose label starts so
  local rows
  rows=$(awk -F'|' -v want="$1" '
    /^## / { in_budget = ($0 == "## The line budget"); next }
    in_budget && NF >= 4 {
      label = $2; gsub(/`/, "", label); gsub(/^[ \t]+|[ \t]+$/, "", label)
      value = $3; gsub(/^[ \t]+|[ \t]+$/, "", value)
      if (index(label, want) == 1) print value
    }' "$table" 2>/dev/null) || rows=""
  if [ "$(grep -c . <<< "$rows")" -ne 1 ] || ! [[ "$rows" =~ ^[0-9]+$ ]]; then
    echo "UNPARSEABLE cap table $table: need exactly one whole-number '$1' row" >&2; exit 1
  fi
  echo "$rows"
}
skill_cap=$(read_cap "Any skill")
agent_cap=$(read_cap "Any agent")
gate_cap=$(read_cap "Any gate")
status_report_cap=$(read_cap "status-report.md")
fail=0
check() {
  local n
  n=$(wc -l < "$1" | tr -d ' ')
  if [ "$n" -gt "$2" ]; then echo "OVER CAP $1: $n > $2"; fail=1; fi
}
check_skill() {
  local dir n
  dir="$(dirname "$1")"
  local files=("$1")
  while IFS= read -r ref; do files+=("$ref"); done \
    < <(find "$dir/references" -name '*.md' 2>/dev/null | sort)
  n=$(cat "${files[@]}" | wc -l | tr -d ' ')
  if [ "$n" -gt "$2" ]; then
    echo "OVER CAP $1 (+references): $n > $2"; fail=1
  else
    echo "ok: $1 (+references) = $n <= $2"
  fi
}
for f in "${skills[@]}"; do check_skill "$f" "$skill_cap"; done
for f in "$root"/agents/*.md; do check "$f" "$agent_cap"; done
for f in "$root"/gates/*.md; do
  if [ "$(basename "$f")" = "status-report.md" ]; then check "$f" "$status_report_cap"; else check "$f" "$gate_cap"; fi
done
exit "$fail"
