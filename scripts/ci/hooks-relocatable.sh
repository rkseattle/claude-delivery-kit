#!/usr/bin/env bash
# The hook self-tests take the hook under test as their argument, so they pass from a copy
# of hooks/ anywhere. A self-test that hardcoded its target would pass in place and fail
# once the plugin is installed elsewhere. Usage: hooks-relocatable.sh [repo-root]
set -euo pipefail
root="${1:-.}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -r "$root/hooks" "$tmp/relocated"
# From the copy's directory, so a self-test resolving `hooks/...` against the working
# directory cannot reach the original.
cd "$tmp"
bash relocated/block-false-stop.sh --self-test
bash relocated/protect-plan-branch.sh --self-test
