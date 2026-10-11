#!/usr/bin/env bash
# A skill or agent whose frontmatter name does not match its path is invisible under the
# name everything else refers to it by. Usage: frontmatter-names.sh [repo-root]
set -euo pipefail
root="${1:-.}"
shopt -s nullglob
skills=("$root"/skills/*/SKILL.md)
[ "${#skills[@]}" -gt 0 ] || { echo "no skills/*/SKILL.md under $root"; exit 1; }
fail=0
name_of() { awk '/^---$/{c++;next} c==1 && /^name:/{print $2; exit}' "$1"; }
for f in "${skills[@]}"; do
  want=$(basename "$(dirname "$f")"); got=$(name_of "$f")
  [ "$want" = "$got" ] || { echo "MISMATCH $f: dir=$want name=$got"; fail=1; }
done
for f in "$root"/agents/*.md; do
  want=$(basename "$f" .md); got=$(name_of "$f")
  [ "$want" = "$got" ] || { echo "MISMATCH $f: file=$want name=$got"; fail=1; }
done
exit "$fail"
