#!/usr/bin/env bash
# Each check passes on a clean copy of the repo and fails on a copy carrying a defect it
# exists to catch, one case per branch of the check. A check whose only failure mode is
# silence looks exactly like a clean run, so this is what proves the checks still bite.
# Usage: self-test.sh [repo-root]
set -uo pipefail
root="$(cd "${1:-.}" && pwd)"
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail=0

fresh_copy() {
  rm -rf "$tmp/repo"; mkdir -p "$tmp/repo"
  local files f
  files=$(git -C "$root" ls-files) || { echo "cannot list tracked files"; exit 1; }
  while IFS= read -r f; do
    mkdir -p "$tmp/repo/$(dirname "$f")"
    cp -p "$root/$f" "$tmp/repo/$f" || { echo "cannot copy tracked file $f"; exit 1; }
  done <<< "$files"
  { git -C "$tmp/repo" init -q && git -C "$tmp/repo" add -A --force; } \
    || { echo "cannot stage the copy"; exit 1; }
}

report() {  # report <want> <got> <check> <description>
  if [ "$2" = "$1" ]; then echo "ok   $3: $4"; else echo "FAIL $3: $4 (expected $1, got $2)"; fail=1; fi
}

expect() {  # expect <pass|fail> <description> <check> [root] — root defaults to the copy
  local got
  if bash "$here/$3" "${4:-$tmp/repo}" > /dev/null 2>&1; then got=pass; else got=fail; fi
  report "$1" "$got" "$3" "$2"
}

# Every check script gets a clean-copy case, so a new check cannot be added without one.
for path in "$here"/*.sh; do
  check="$(basename "$path")"
  case "$check" in all.sh|self-test.sh) continue ;; esac
  fresh_copy; expect pass "clean copy" "$check"
done

mkdir -p "$tmp/empty"
for check in json-parses.sh bundled-refs.sh no-leaks.sh frontmatter-names.sh line-budget.sh; do
  expect fail "a root with nothing to scan" "$check" "$tmp/empty"
done

mkdir -p "$tmp/nojson" && git -C "$tmp/nojson" init -q
expect fail "a repository with no tracked JSON files" json-parses.sh "$tmp/nojson"

fresh_copy; printf '{bad' > "$tmp/repo/.claude-plugin/plugin.json"
expect fail "a malformed file that is not the last one listed" json-parses.sh
fresh_copy; printf '{bad' > "$tmp/repo/new.json"; git -C "$tmp/repo" add new.json
expect fail "a newly tracked malformed file" json-parses.sh

fresh_copy; chmod -x "$tmp/repo/hooks/block-false-stop.sh"
expect fail "a hook command that is not executable" hooks-wired.sh
fresh_copy; jq 'del(.hooks.Stop)' "$root/hooks/hooks.json" > "$tmp/repo/hooks/hooks.json"
expect fail "no Stop hook entry" hooks-wired.sh
fresh_copy; jq 'del(.hooks.PostToolUse)' "$root/hooks/hooks.json" > "$tmp/repo/hooks/hooks.json"
expect fail "no PostToolUse Bash entry" hooks-wired.sh
fresh_copy; jq '.hooks.PreToolUse = [{"matcher": "Bash", "hook": [{"command": "x"}]}]' \
  "$root/hooks/hooks.json" > "$tmp/repo/hooks/hooks.json"
expect fail "an entry whose hooks key is misspelled" hooks-wired.sh

for hook in block-false-stop protect-plan-branch; do
  fresh_copy; sed -i.bak "s#^hook_under_test=.*#hook_under_test=\"hooks/$hook.sh\"#" \
    "$tmp/repo/hooks/$hook.self-test.sh"
  expect fail "$hook's self-test resolving the hook against the working directory" hooks-relocatable.sh
done

fresh_copy; sed -i.bak 's/^name: deliver$/name: delivery/' "$tmp/repo/skills/deliver/SKILL.md"
expect fail "a skill whose frontmatter name differs from its directory" frontmatter-names.sh
fresh_copy; sed -i.bak 's/^name: commit-adversary$/name: commit-reviewer/' "$tmp/repo/agents/commit-adversary.md"
expect fail "an agent whose frontmatter name differs from its file" frontmatter-names.sh

fresh_copy; yes x | head -n 481 > "$tmp/repo/skills/deliver/references/padding.md"
expect fail "text moved into a skill's references/ past the cap" line-budget.sh
fresh_copy; yes x | head -n 141 >> "$tmp/repo/agents/commit-adversary.md"
expect fail "an agent past its cap" line-budget.sh
fresh_copy; yes x | head -n 141 >> "$tmp/repo/gates/status-report.md"
expect fail "status-report.md past its tighter cap" line-budget.sh
fresh_copy; yes x | head -n 301 > "$tmp/repo/gates/padding.md"
expect fail "a gate past its cap" line-budget.sh

mkdir -p "$tmp/norefs/skills" "$tmp/norefs/gates" "$tmp/norefs/agents"
echo "no references here" > "$tmp/norefs/gates/plain.md"
expect fail "directories present but no references in them" bundled-refs.sh "$tmp/norefs"

fresh_copy; printf '%s\n' "Read \${CLAUDE_PLUGIN_ROOT}/gates/does-not-exist.md here." >> "$tmp/repo/gates/pre-push.md"
expect fail "a reference to a file that does not exist" bundled-refs.sh

fresh_copy; printf '%s\n' 'Run xcodebuild test.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a build-tool invocation in a shared file" no-leaks.sh
fresh_copy; printf '%s\n' 'See ABC-123.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a ticket ID in a shared file" no-leaks.sh
fresh_copy; printf '%s\n' 'acme-widgets' > "$tmp/repo/.github/consumers.txt"
printf '%s\n' 'Built for acme-widgets.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a consuming project named in a shared file" no-leaks.sh

fresh_copy; sed -i.bak '/no-leaks/d' "$tmp/repo/scripts/ci/all.sh"
expect fail "a CI step with no line in all.sh" ci-steps-mirrored.sh
fresh_copy; sed -i.bak '/no-leaks/d' "$tmp/repo/.claude/gates/pre-push-mechanics.md"
expect fail "a CI step with no row in the mechanics table" ci-steps-mirrored.sh
fresh_copy; sed -i.bak -e 's#^bash scripts/ci/json-parses.sh$#SWAP#' \
  -e 's#^bash scripts/ci/frontmatter-names.sh$#bash scripts/ci/json-parses.sh#' \
  -e 's#^SWAP$#bash scripts/ci/frontmatter-names.sh#' "$tmp/repo/scripts/ci/all.sh"
expect fail "all.sh running CI's steps out of order" ci-steps-mirrored.sh

fresh_copy; printf '%s\n' '' '      - name: Shellcheck' '        uses: ludeeus/action-shellcheck@master' \
  >> "$tmp/repo/.github/workflows/ci.yml"
expect fail "a CI step that is an action with no run: line" ci-steps-mirrored.sh
fresh_copy; jq 'del(.mechanics_gate_pre_push)' "$root/.claude/project.json" > "$tmp/repo/.claude/project.json"
expect fail "project.json naming no mechanics gate" ci-steps-mirrored.sh
fresh_copy; jq '.mechanics_gate_pre_push = "none"' "$root/.claude/project.json" > "$tmp/repo/.claude/project.json"
expect fail "a mechanics gate set to none" ci-steps-mirrored.sh
fresh_copy; sed -i.bak '/^ *run: /d' "$tmp/repo/.github/workflows/ci.yml"
expect fail "a ci.yml with no run: steps" ci-steps-mirrored.sh

fresh_copy; printf '%s\n' '' '      - name: Multi-line' '        run: |' '          echo one' \
  >> "$tmp/repo/.github/workflows/ci.yml"
expect fail "a multi-line run: block" ci-steps-mirrored.sh
fresh_copy; printf '%s\n' '' '      - name: Mentions run: in its name' '        uses: some/action@v1' \
  >> "$tmp/repo/.github/workflows/ci.yml"
expect fail "an action whose step name contains run:" ci-steps-mirrored.sh
fresh_copy; sed -i.bak '/No project-specific tokens/d' "$tmp/repo/.claude/gates/pre-push-mechanics.md"
printf '%s\n' "Also see \`bash scripts/ci/no-leaks.sh\`." >> "$tmp/repo/.claude/gates/pre-push-mechanics.md"
expect fail "a command mentioned in prose but missing from the table" ci-steps-mirrored.sh

exit "$fail"
