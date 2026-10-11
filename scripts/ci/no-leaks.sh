#!/usr/bin/env bash
# The kit must not acquire a rule that only makes sense in one project: "Shared before
# project", checked rather than trusted. Usage: no-leaks.sh [repo-root]
#
# Shape rules catch build-tool invocations, language-specific manifests, and ticket-prefix
# patterns. Consuming project names live in the gitignored .github/consumers.txt, because a
# public guard that named them would itself be the leak.
set -euo pipefail
root="${1:-.}"
cd "$root"
# grep exits 1 for no match and 2 for an error such as a missing directory; only 1 is clean.
scan() {
  local rc=0
  grep -rniE "$@" skills gates agents || rc=$?
  case "$rc" in
    0) return 1 ;;
    1) return 0 ;;
    *) echo "cannot scan skills, gates and agents under $PWD"; exit 1 ;;
  esac
}
if ! scan '\.(lproj|pbxproj|xctestplan)\b|xcodebuild|swiftlint|swiftformat|\bpool\.query\b|npm run [a-z_:]+|\b[A-Z]{3,10}-[0-9]+\b'; then
  echo "a project-specific token reached a shared file"; exit 1
fi
if [ -f .github/consumers.txt ] && ! scan -f .github/consumers.txt; then
  echo "a consuming project was named in a shared file"; exit 1
fi
echo "clean"
