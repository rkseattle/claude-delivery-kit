#!/usr/bin/env bash
# Every tracked JSON file parses. Usage: json-parses.sh [repo-root]
#
# Files come from `git ls-files`, so a newly tracked JSON file is checked without an edit
# here; run it after `git add`, since an untracked file is not seen. Each failure sets a flag rather than relying on `set -e`, which ignores a failure
# on the left of `&&` and would let only the last file decide the result.
set -uo pipefail
root="${1:-.}"
files=$(git -C "$root" ls-files '*.json') || { echo "cannot list tracked files under $root"; exit 1; }
[ -n "$files" ] || { echo "no tracked JSON files under $root"; exit 1; }
fail=0
while IFS= read -r f; do
  if err=$(python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$root/$f" 2>&1); then
    echo "ok: $f"
  else
    echo "BROKEN: $f: ${err##*$'\n'}"
    fail=1
  fi
done <<< "$files"
exit "$fail"
