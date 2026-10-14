#!/usr/bin/env bash
# The kit must not acquire a rule that only makes sense in one project: "Shared before
# project", checked rather than trusted. Usage: no-leaks.sh [repo-root]
#
# Shape rules catch build-tool invocations, language-specific manifests, and ticket-prefix
# patterns. Consuming project names live in the gitignored .github/consumers.txt, because a
# public guard that named them would itself be the leak.
set -euo pipefail
# Match bytes, so a stray invalid UTF-8 byte cannot hide a line. The built-in patterns are
# ASCII; consumer names in consumers.txt are matched case-insensitively for ASCII only.
export LC_ALL=C
root="${1:-.}"
cd "$root"
# scan <allowed> <grep args...> fails on any `path:line:` match not matching <allowed>, an
# extended regex ('' allows nothing). -a prints matches in files grep would call binary,
# which it otherwise reports only on stderr. grep exits 1 for no match and 2 for an error
# such as a missing directory or a bad pattern; only 0 and 1 are a completed scan.
scan() {
  local allowed="$1" rc=0 out
  shift
  out=$(grep -rna "$@" skills gates agents) || rc=$?
  [ "$rc" -le 1 ] || { echo "cannot scan skills, gates and agents under $PWD"; exit 1; }
  if [ -n "$allowed" ]; then
    rc=0; out=$(grep -vE "$allowed" <<< "$out") || rc=$?
    [ "$rc" -le 1 ] || { echo "cannot apply the allowlist $allowed"; exit 1; }
  fi
  [ -z "$out" ] || { echo "$out"; return 1; }
}
if ! scan '' -iE '\.(lproj|pbxproj|xctestplan)\b|xcodebuild|swiftlint|swiftformat|\bpool\.query\b|npm run [a-z_:]+'; then
  echo "a project-specific token reached a shared file"; exit 1
fi
# Jira project keys are uppercase by definition, so this scan is case-sensitive; standard
# identifiers that share a key's shape (UTF-8, SHA-256, ISO-8601) are allowed by prefix,
# which also passes a real project keyed with one of those prefixes.
if ! scan ':(UTF|SHA|ISO|RFC|PEP|CVE|GPL|LGPL|AGPL|MPL|IEEE|ECMA)-[0-9]+$' -oE '\b[A-Z]{3,10}-[0-9]+\b'; then
  echo "a ticket ID reached a shared file"; exit 1
fi
if [ -f .github/consumers.txt ] && ! scan '' -iE -f .github/consumers.txt; then
  echo "a consuming project was named in a shared file"; exit 1
fi
echo "clean"
