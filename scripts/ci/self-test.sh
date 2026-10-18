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

expect_saying() {  # expect_saying <description> <check> <text> [root] — exit 1, and <text> in the output
  local out got rc=0
  out=$(bash "$here/$2" "${4:-$tmp/repo}" 2>&1) || rc=$?
  if [ "$rc" = 1 ] && grep -qF -- "$3" <<< "$out"; then got=fail; else got="exit $rc without '$3'"; fi
  report fail "$got" "$2" "$1"
}

# Every check script gets a clean-copy case, so a new check cannot be added without one.
for path in "$here"/*.sh; do
  check="$(basename "$path")"
  case "$check" in all.sh|self-test.sh) continue ;; esac
  fresh_copy; expect pass "clean copy" "$check"
done

mkdir -p "$tmp/empty"
for check in json-parses.sh bundled-refs.sh no-leaks.sh frontmatter-names.sh line-budget.sh shellcheck.sh \
             actions-pinned.sh rule-book-map.sh; do
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
caps=skills/deliver/references/invariants.md
for row in "Any skill|skills/deliver/SKILL.md" "Any agent|agents/design-adversary.md" \
           "Any gate|gates/pre-push.md" "status-report.md|gates/status-report.md"; do
  fresh_copy; sed -i.bak -E "s/^(\\| [\`]?${row%%|*}[^|]*\\| *)[0-9]+/\\1100/" "$tmp/repo/$caps"
  expect_saying "the ${row%%|*} cap set to 100 in the table" line-budget.sh "OVER CAP $tmp/repo/${row#*|}"
done
fresh_copy; sed -i.bak '/^| Any agent/d' "$tmp/repo/$caps"
expect_saying "a cap table with no Any agent row" line-budget.sh "UNPARSEABLE cap table"
fresh_copy; sed -i.bak '/^| Any agent/p' "$tmp/repo/$caps"
expect_saying "a cap table with two Any agent rows" line-budget.sh "UNPARSEABLE cap table"
fresh_copy; sed -i.bak -E 's/^(\| Any agent[^|]*\| *)[0-9]+/\1x/' "$tmp/repo/$caps"
expect_saying "a cap table whose Any agent cap is not a number" line-budget.sh "UNPARSEABLE cap table"
fresh_copy; printf '%s\n' '' '## Elsewhere' '' '| Any agent | 1 |' >> "$tmp/repo/$caps"
# The appended lines count against deliver's own skill cap; lift it so only the agent row is tested.
sed -i.bak -E 's/^(\| Any skill[^|]*\| *)[0-9]+/\19999/' "$tmp/repo/$caps"
expect pass "an Any agent row outside the line budget section" line-budget.sh
expect_saying "a root with no skills" line-budget.sh "no skills/*/SKILL.md" "$tmp/empty"
fresh_copy; rm "$tmp/repo/$caps"
expect_saying "no cap table file" line-budget.sh "UNPARSEABLE cap table $tmp/repo/$caps: no such file"

mkdir -p "$tmp/norefs/skills" "$tmp/norefs/gates" "$tmp/norefs/agents"
echo "no references here" > "$tmp/norefs/gates/plain.md"
expect fail "directories present but no references in them" bundled-refs.sh "$tmp/norefs"

fresh_copy; printf '%s\n' "Read \${CLAUDE_PLUGIN_ROOT}/gates/does-not-exist.md here." >> "$tmp/repo/gates/pre-push.md"
expect fail "a reference to a file that does not exist" bundled-refs.sh
fresh_copy; printf '%s\377\n' "Read \${CLAUDE_PLUGIN_ROOT}/gates/does-not-exist.md here." >> "$tmp/repo/gates/pre-push.md"
expect fail "a broken reference on a line with an invalid UTF-8 byte" bundled-refs.sh
fresh_copy; printf '%s\0\n' "Read \${CLAUDE_PLUGIN_ROOT}/gates/does-not-exist.md here." >> "$tmp/repo/gates/pre-push.md"
expect fail "a broken reference in a file grep calls binary" bundled-refs.sh

# Each map line is assembled by printf at runtime, its backticks passed in as arguments.
map=reference/rule-book-map.md bt='`'
fresh_copy; printf '| Z1 | x | %sgates/does-not-exist.md%s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a map row naming a missing path" rule-book-map.sh "MISSING: gates/does-not-exist.md"
fresh_copy; printf '| Z1 | x | %sgates/does-not-exist.md%s | x |\n' "$bt$bt" "$bt$bt" >> "$tmp/repo/$map"
expect_saying "a missing path in a double-backtick span" rule-book-map.sh "MISSING: gates/does-not-exist.md"
fresh_copy; printf '| Z1 | %sgates/pre-push.md%s | %sgates/does-not-exist.md%s |\n' "$bt" "$bt" "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a missing path in a line's second span" rule-book-map.sh "MISSING: gates/does-not-exist.md"
fresh_copy; printf '| Z1 | %sx%sgates/does-not-exist.md%s | x |\n' "$bt$bt" "$bt" "$bt$bt" >> "$tmp/repo/$map"
expect_saying "a span holding a shorter backtick run" rule-book-map.sh "MISSING: x${bt}gates/does-not-exist.md"
fresh_copy; printf '\nSee %sgates/does-not-\nexist.md%s here.\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a span broken across lines, read as one" rule-book-map.sh "MISSING: gates/does-not- exist.md"
fresh_copy; printf '| Z1 | \\%sgates/does-not-exist.md%s | x |\n' "$bt$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a two-backtick run whose first is escaped, opening a one-backtick span" rule-book-map.sh \
  "MISSING: gates/does-not-exist.md"
fresh_copy; printf '| Z1 | \\\\%sgates/does-not-exist.md%s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "an escaped backslash before a span, which still opens" rule-book-map.sh \
  "MISSING: gates/does-not-exist.md"
for climb in ../ gates/../../x; do
  fresh_copy; printf '| Z1 | %s%s%s | x |\n' "$bt" "$climb" "$bt" >> "$tmp/repo/$map"
  expect_saying "a path $climb climbing out of the repo" rule-book-map.sh "MISSING: $climb"
done
fresh_copy; printf '| Z1 | %s gates/pre-push.md%s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a span padded on one side only, which keeps its space" rule-book-map.sh "MISSING:  gates/pre-push.md"
fresh_copy; printf 'x\n' > "$tmp/repo/gates/untracked.md"
printf '| Z1 | %sgates/untracked.md%s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a path on disk that git does not track" rule-book-map.sh "MISSING: gates/untracked.md"
fresh_copy; printf '| Z1 | %sGates/pre-push.md%s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a tracked path cased wrongly" rule-book-map.sh "MISSING: Gates/pre-push.md"
fresh_copy; printf '| Z1 | %s.github/workflows/ci.yml%s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect pass "a tracked path under a dot-directory" rule-book-map.sh
fresh_copy; printf '| Z1 | %s gates/pre-push.md %s | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect pass "a path span padded with one space each side" rule-book-map.sh
fresh_copy; printf '| Z1 | %sno-such-token%s | gates/does-not-exist.md | x |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect pass "a backticked token with no slash, and a missing path outside backticks" rule-book-map.sh
fresh_copy; printf '| Z1 | \\%s %sgates/does-not-exist.md%s | x |\n' "$bt" "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "an escaped backtick before a span" rule-book-map.sh "MISSING: gates/does-not-exist.md"
fresh_copy; printf '%s%s%s\ngates/does-not-exist.md\n%s%s%s\n' "$bt" "$bt" "$bt" "$bt" "$bt" "$bt" >> "$tmp/repo/$map"
expect pass "a missing path inside a fenced block, which is no span" rule-book-map.sh
fresh_copy; printf '# Map\nNo %spaths%s here.\n' "$bt" "$bt" > "$tmp/repo/$map"
expect_saying "a map naming no path" rule-book-map.sh "names no path"
fresh_copy; printf '| Z1 | %sgates/pre-push.md%s | \377 |\n' "$bt" "$bt" >> "$tmp/repo/$map"
expect_saying "a map holding an invalid UTF-8 byte" rule-book-map.sh "is not UTF-8"
# Each exception case cites a fixture row it appends to the Kit-wide table, which ends the
# register, so renewing or remediating a live row never rewrites these cases.
ex=gates/exceptions.md
row() { printf '| Z1 | x | %sgates/exceptions.md%s | x | %s |\n' "$bt" "$bt" "$1" >> "$tmp/repo/$map"; }
fixture() {  # fixture [expiry] [remediation]: the Rule book R90 row, cited by the map
  printf '| Rule book R90: fixture | x | x | %s | %s |\n' "${1:-2099-01-01}" "${2-x}" >> "$tmp/repo/$ex"
  row 'Rule book R90'
}
fresh_copy; fixture
expect pass "a cited fixture row" rule-book-map.sh
fresh_copy; row 'Rule book R90'
expect_saying "the cited row absent" rule-book-map.sh "MISSING ROW: Rule book R90 starts"
fresh_copy; fixture; row 'Rule book R9'
expect_saying "a name that only prefixes another row" rule-book-map.sh "MISSING ROW: Rule book R9 starts"
fresh_copy; fixture; row 'Rule book R90; Rule book R97'
expect_saying "a bad name beside a good one in one cell" rule-book-map.sh "MISSING ROW: Rule book R97 starts"
fresh_copy; fixture; row 'Rule book R90;'
expect pass "a trailing semicolon in an Excepted by cell" rule-book-map.sh
fresh_copy; fixture; row 'Rule book    R90'
expect pass "a name with a run of spaces" rule-book-map.sh
fresh_copy; printf '| Rule book   R90: fixture | x | x | 2099-01-01 | x |\n' >> "$tmp/repo/$ex"; row 'Rule book R90'
expect pass "a Rule cell with a run of spaces" rule-book-map.sh
fresh_copy; fixture 2099-01-01 ''
expect_saying "the cited row with its Remediation cell empty" rule-book-map.sh "MISSING ROW: Rule book R90 starts"
fresh_copy; fixture 2099-01-01 ---
expect_saying "the cited row with a separator for its Remediation" rule-book-map.sh "MISSING ROW: Rule book R90 starts"
fresh_copy; fixture TBD
expect_saying "the cited row with an Expiry that is no date" rule-book-map.sh "MISSING ROW: Rule book R90 starts"
fresh_copy; fixture 2000-01-01
expect pass "the cited row expired, which deliver reports instead" rule-book-map.sh
fresh_copy; printf '\n## Elsewhere\n\n| Rule | Reason | Risk | Expiry | Remediation |\n| --- | --- | --- | --- | --- |\n| Rule book R90: x | x | x | 2099-01-01 | x |\n' \
  >> "$tmp/repo/$ex"; row 'Rule book R90'
expect_saying "the cited name only in a complete row outside Kit-wide exceptions" rule-book-map.sh \
  "MISSING ROW: Rule book R90 starts"
fresh_copy; awk '/^\| Rule \| Reason \|/ && !done { print "### Held"; print ""; done = 1 } { print }' \
  "$root/$ex" > "$tmp/repo/$ex"; fixture
expect pass "a sub-heading inside Kit-wide exceptions" rule-book-map.sh
fresh_copy; sed -i.bak 's/^| Rule | Reason | Risk | Expiry | Remediation |$/| Reason | Rule | Risk | Expiry | Remediation |/' \
  "$tmp/repo/$ex"; fixture
expect_saying "a Kit-wide table with its columns reordered" rule-book-map.sh "NOT A REGISTER"
fresh_copy; printf '\n| ID | Rule |\n| --- | --- |\n| Z1 | x |\n' >> "$tmp/repo/$map"
expect_saying "a map table with no Excepted by column" rule-book-map.sh "NO EXCEPTED BY COLUMN"
fresh_copy; printf '\nExcepted under the kit-wide row "Rule book R99".\n' >> "$tmp/repo/$map"
expect pass "an exception named in prose, which is no citation" rule-book-map.sh
fresh_copy; rm "$tmp/repo/$ex"
expect_saying "no exceptions register" rule-book-map.sh "no exceptions register"
sed -i.bak -E 's/^(\| [A-Z][0-9][0-9.A-Z]* \|.*\|) [^|]+ \|$/\1  |/' "$tmp/repo/$map"
expect pass "no exceptions register, and no row citing one" rule-book-map.sh
mkdir -p "$tmp/nogit/reference" && cp "$root/$map" "$tmp/nogit/$map"
expect_saying "a map in a root git cannot list" rule-book-map.sh "cannot list the tracked files" "$tmp/nogit"

fresh_copy; printf '%s\n' 'Run xcodebuild test.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a build-tool invocation in a shared file" no-leaks.sh
fresh_copy; printf '%s\n' 'See ABC-123.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a ticket ID in a shared file" no-leaks.sh
fresh_copy; printf '%s\n' 'Run XcodeBuild test.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a build-tool invocation in mixed case" no-leaks.sh
fresh_copy; printf '%s\n' 'Encode as utf-8 for node-20.' >> "$tmp/repo/gates/pre-push.md"
expect pass "a lowercase word-digit token" no-leaks.sh
fresh_copy; printf '%s\n' 'Write UTF-8, SHA-256, ISO-8601.' >> "$tmp/repo/gates/pre-push.md"
expect pass "an allowlisted standard identifier" no-leaks.sh
fresh_copy; printf '%s\n' 'Write UTF-8 per ABC-123.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a ticket ID beside an allowlisted identifier" no-leaks.sh
fresh_copy; printf '%s\n' 'See abc-123.' >> "$tmp/repo/gates/pre-push.md"
expect pass "a lowercase ticket ID, an accepted narrowing" no-leaks.sh
fresh_copy; printf '%s\n' 'See XSHA-12 and ISOX-9.' >> "$tmp/repo/gates/pre-push.md"
expect fail "a ticket ID containing an allowlisted prefix" no-leaks.sh
fresh_copy; printf 'See ABC-123.\377\n' >> "$tmp/repo/gates/pre-push.md"
expect fail "a ticket ID on a line with an invalid UTF-8 byte" no-leaks.sh
fresh_copy; printf 'See ABC-123.\0\n' >> "$tmp/repo/gates/pre-push.md"
expect fail "a ticket ID in a file grep calls binary" no-leaks.sh
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

# Each workflow line is assembled by printf at runtime rather than written out.
sha=11d5960a326750d5838078e36cf38b85af677262
for ref in "v4|a tag" "${sha:0:7}|a 7-character short SHA" "main|a branch name" "${sha}0|a 41-character ref"; do
  fresh_copy; printf '      - uses: %s@%s\n' actions/checkout "${ref%%|*}" >> "$tmp/repo/.github/workflows/ci.yml"
  expect_saying "a uses: line naming ${ref#*|}" actions-pinned.sh "NOT PINNED"
done
fresh_copy; printf '      - uses: "%s@%s"\n' actions/checkout v4 >> "$tmp/repo/.github/workflows/ci.yml"
expect_saying "a quoted uses: line naming a tag" actions-pinned.sh "NOT PINNED"
fresh_copy; printf '  %s:\n    uses: %s@%s\n' reuse org/repo/.github/workflows/build.yml main \
  >> "$tmp/repo/.github/workflows/ci.yml"
expect_saying "a job-level reusable workflow on a branch" actions-pinned.sh "NOT PINNED"
fresh_copy; printf 'on: push\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: %s@%s\n' \
  actions/checkout v4 > "$tmp/repo/.github/workflows/other.yaml"
expect_saying "a .yaml workflow naming a tag" actions-pinned.sh "NOT PINNED"
fresh_copy; printf '      # - uses: %s@%s\n' actions/checkout v4 >> "$tmp/repo/.github/workflows/ci.yml"
expect pass "a commented-out uses: line" actions-pinned.sh
fresh_copy; printf '      - uses: %s\n      - uses: "%s"\n      - uses: %s   #  v4\n' \
  "actions/checkout@$sha" "actions/checkout@$sha" "actions/checkout@$sha" >> "$tmp/repo/.github/workflows/ci.yml"
expect pass "a pinned line bare, quoted, and with a spaced comment" actions-pinned.sh
for form in "uses : |@v4|a space before the colon" "{uses: |@v4}|a flow mapping" \
            "uses: |@v4 # was uses: actions/checkout@$sha|a pinned ref only in its comment" \
            "uses: docker://|:3.20|a docker image by tag" "uses: [|@v4]|a uses: that is not a string"; do
  IFS='|' read -r before after name <<< "$form"
  fresh_copy; printf '      - %s%s%s\n' "$before" actions/checkout "$after" >> "$tmp/repo/.github/workflows/ci.yml"
  expect_saying "a uses: line with $name" actions-pinned.sh "NOT PINNED"
done
fresh_copy; printf '      - uses: ./%s\n      - uses: docker://alpine@sha256:%s\n      - run: |\n          uses: %s@%s\n' \
  .github/actions/local "$(printf 'a%.0s' {1..64})" actions/checkout v4 >> "$tmp/repo/.github/workflows/ci.yml"
expect pass "a local action, a docker digest, and uses: text inside a run: block" actions-pinned.sh
fresh_copy; printf '      - uses: "%s@%s'"'"'\n' actions/checkout "$sha" >> "$tmp/repo/.github/workflows/ci.yml"
expect_saying "a workflow YAML cannot parse" actions-pinned.sh "UNPARSEABLE"
fresh_copy; printf 'on: push\n' > "$tmp/repo/.github/workflows/other.yml"
expect_saying "a workflow with no jobs: mapping" actions-pinned.sh "UNPARSEABLE"

fresh_copy; sed -i.bak '/^    if: always()$/d' "$tmp/repo/.github/workflows/ci.yml"
expect fail "the aggregate job without if: always()" all-jobs-passed.sh
fresh_copy; sed -i.bak 's/^    needs: \[hooks, script-tests, manifest\]$/    needs: [hooks, manifest]/' \
  "$tmp/repo/.github/workflows/ci.yml"
expect fail "the aggregate job not needing every job" all-jobs-passed.sh
fresh_copy
ok3='"hooks":{"result":"success"},"script-tests":{"result":"success"}'
for results in "{$ok3,\"manifest\":{\"result\":\"failure\"}}" \
               "{$ok3,\"manifest\":{\"result\":\"cancelled\"}}" \
               '{"hooks":{"result":"success"},"manifest":{"result":"success"}}' 'not json' '{}'; do
  if NEEDS="$results" bash "$here/all-jobs-passed.sh" "$tmp/repo" > /dev/null 2>&1; then got=pass; else got=fail; fi
  report fail "$got" all-jobs-passed.sh "job results $results"
done
for results in "{$ok3,\"manifest\":{\"result\":\"success\"}}" "{$ok3,\"manifest\":{\"result\":\"skipped\"}}"; do
  if NEEDS="$results" bash "$here/all-jobs-passed.sh" "$tmp/repo" > /dev/null 2>&1; then got=pass; else got=fail; fi
  report pass "$got" all-jobs-passed.sh "job results $results"
done

exit "$fail"
