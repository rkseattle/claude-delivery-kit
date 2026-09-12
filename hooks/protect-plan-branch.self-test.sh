#!/usr/bin/env bash
# Self-test for protect-plan-branch.sh. Separate file so the hook stays within the
# 60-line-ish ceiling that exists to stop it growing the way its predecessor did.
#
# Asserts exact counts, not exit status: a guard that silently stops restoring is
# indistinguishable from a clean run if you only check whether it passed.
#
# The predecessor's suite was 384 lines of command-string cases — `env -S`, `xargs
# --arg-file`, backslash-newline continuations — because that guard parsed the command
# and every spelling was a separate risk. This one asks git where HEAD is, so the
# command that moved it is irrelevant and none of those cases have anything to assert.
# What replaces them is the state matrix: where HEAD ended up, what the plan says, and
# whether the tree permits a restore.
set -uo pipefail

hook_under_test="${1:?usage: protect-plan-branch.self-test.sh <path-to-hook>}"
hook="$(cd "$(dirname "$hook_under_test")" && pwd)/$(basename "$hook_under_test")"

failures=0
total=0

# A repo on `feature` with a committed file, plus plan state naming the branch given.
# Every case starts from this and diverges, so a case cannot inherit another's HEAD.
make_repo() {
  local dir="$1" plan_branch="${2-feature}"
  mkdir -p "$dir"
  git -C "$dir" init -q
  git -C "$dir" config user.email test@example.com
  git -C "$dir" config user.name test
  git -C "$dir" symbolic-ref HEAD refs/heads/main
  printf 'one\n' > "$dir/tracked.txt"
  git -C "$dir" add tracked.txt
  git -C "$dir" commit -qm one
  git -C "$dir" checkout -qb feature
  printf 'two\n' > "$dir/tracked.txt"
  git -C "$dir" commit -qam two
  mkdir -p "$dir/.claude/state"
  if [ -n "$plan_branch" ]; then
    printf '{"branch": "%s", "phases": []}\n' "$plan_branch" > "$dir/.claude/state/current-plan.json"
  fi
}

# Marks the plan branch as one the hook has seen HEAD sitting on, which is what licenses a
# restore. Cases that assert a restore must call this: without it the hook reads the
# mismatch as a session that was never on the branch and correctly leaves HEAD alone.
adopt() {
  local dir="$1" branch="${2-feature}"
  mkdir -p "$dir/.claude/state"
  printf '%s\n' "$branch" > "$dir/.claude/state/branch-adopted"
}

# Runs the hook against a repo and echoes the verdict it logged. The log is the
# assertion surface because it records what the hook DID; stdout only describes it.
#
# stdout goes to a FILE rather than a variable: every caller runs this inside `$(...)`,
# which is a subshell, so an assignment here would be discarded before expect_stdout
# could read it — and every stdout assertion would then test an empty string and fail
# no matter what the hook printed.
run_hook() {
  local dir="$1"
  : > "$dir/.claude/state/hook-invocations.log" 2>/dev/null || true
  printf '{"cwd": "%s", "tool_name": "Bash", "tool_input": {"command": "irrelevant"}}' "$dir" \
    | CLAUDE_PROJECT_DIR="$dir" bash "$hook" > "$tmp/last-stdout" 2>/dev/null
  grep -o 'verdict=[a-z-]*' "$dir/.claude/state/hook-invocations.log" 2>/dev/null | tail -n 1 | sed 's/verdict=//'
}

# expect <verdict> <expected-branch-after> <label> — sets up nothing; the caller has
# already built $tmp/repo into the state under test.
expect() {
  local want_verdict="$1" want_head="$2" label="$3" got_verdict got_head
  total=$((total + 1))
  got_verdict=$(run_hook "$tmp/repo")
  got_head=$(git -C "$tmp/repo" branch --show-current 2>/dev/null)
  [ -z "$got_head" ] && got_head="DETACHED"
  if [ "$got_verdict" != "$want_verdict" ] || [ "$got_head" != "$want_head" ]; then
    printf '  FAIL: %s\n        verdict: want %s, got %s\n        HEAD:    want %s, got %s\n' \
      "$label" "$want_verdict" "${got_verdict:-<none>}" "$want_head" "$got_head"
    failures=$((failures + 1))
  else
    printf '  ok: %s\n' "$label"
  fi
}

# Asserts on the hook's stdout from the most recent expect/run_hook call.
expect_stdout() {
  local mode="$1" needle="$2" label="$3" out
  out=$(cat "$tmp/last-stdout" 2>/dev/null || true)
  total=$((total + 1))
  case "$mode" in
    contains) if [[ "$out" == *"$needle"* ]]; then printf '  ok: %s\n' "$label"; return; fi ;;
    empty)    if [ -z "$out" ]; then printf '  ok: %s\n' "$label"; return; fi ;;
    valid-json)
      if printf '%s' "$out" | jq -e . >/dev/null 2>&1; then printf '  ok: %s\n' "$label"; return; fi ;;
  esac
  printf '  FAIL: %s\n        stdout was: %s\n' "$label" "${out:-<empty>}"
  failures=$((failures + 1))
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "== HEAD already on the plan branch: never act =="
make_repo "$tmp/repo"
expect ok feature "on the plan branch, nothing to do"
expect_stdout empty "" "a no-op emits no output"

echo "== HEAD moved to another branch: restore it =="
rm -rf "$tmp/repo"; make_repo "$tmp/repo"; adopt "$tmp/repo"
git -C "$tmp/repo" checkout -q main
expect restored feature "checkout main is undone"
expect_stdout valid-json "" "restore output is valid JSON"
expect_stdout contains '"hookEventName": "PostToolUse"' "output names the PostToolUse event"
expect_stdout contains "additionalContext" "restore reports through additionalContext"
expect_stdout contains "systemMessage" "restore reports through systemMessage"
expect_stdout contains "restored to 'feature'" "the message names the branch restored to"

echo "== a detached HEAD is off the branch too =="
# The predecessor needed a DETACH_FLAGS list to catch `--detach`/`-d` because a detach
# names no ref. Here it needs nothing: show-current prints empty and empty != feature.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"; adopt "$tmp/repo"
git -C "$tmp/repo" checkout -q --detach HEAD
expect restored feature "detached HEAD is reattached"
expect_stdout contains "detached HEAD" "the message says HEAD was detached"

echo "== a restore blocked by uncommitted work is reported, never claimed =="
# git refuses to overwrite tracked changes, so the restore fails. Reporting that as
# success is the one outcome worse than not restoring at all.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"; adopt "$tmp/repo"
git -C "$tmp/repo" checkout -q main
printf 'conflicting\n' > "$tmp/repo/tracked.txt"
expect restore-failed main "a blocked restore leaves HEAD where it is"
expect_stdout contains "restore failed" "the failure is stated, not hidden"
expect_stdout contains "Do not commit" "the failure warns against committing"
expect_stdout valid-json "" "failure output is valid JSON"

echo "== untracked files do not block a restore =="
rm -rf "$tmp/repo"; make_repo "$tmp/repo"; adopt "$tmp/repo"
git -C "$tmp/repo" checkout -q main
printf 'scratch\n' > "$tmp/repo/untracked.txt"
expect restored feature "an untracked file still allows the restore"
total=$((total + 1))
if [ -f "$tmp/repo/untracked.txt" ]; then
  echo "  ok: the untracked file survived the restore"
else
  echo "  FAIL: the restore destroyed an untracked file"; failures=$((failures + 1))
fi

echo "== a git operation in progress owns HEAD: never act =="
# A rebase detaches HEAD by design. Restoring during one resets the branch to its
# pre-rebase commit and strands the operation's state directory — unrecoverable, and on
# the mandatory pre-push path rather than an edge case. The conflicted case must not
# report a failed restore either: there is nothing to restore, so there is no failure.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q main
printf 'diverged\n' > "$tmp/repo/tracked.txt"
git -C "$tmp/repo" commit -qam diverged
git -C "$tmp/repo" checkout -q feature
git -C "$tmp/repo" rebase main >/dev/null 2>&1
expect skip DETACHED "a conflicted rebase is left alone"
expect_stdout empty "" "a rebase in progress emits no output"

# The dangerous case: a clean rebase stopped partway. Here the checkout SUCCEEDS, so
# without the guard the replayed commits are silently discarded.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q feature
printf 'three\n' > "$tmp/repo/other.txt"
git -C "$tmp/repo" add other.txt
git -C "$tmp/repo" commit -qm three
git -C "$tmp/repo" checkout -q main
printf 'unrelated\n' > "$tmp/repo/mainonly.txt"
git -C "$tmp/repo" add mainonly.txt
git -C "$tmp/repo" commit -qm mainonly
git -C "$tmp/repo" checkout -q feature
before_head=$(git -C "$tmp/repo" rev-parse feature)
GIT_SEQUENCE_EDITOR="sed -i.bak '1a\\
break' " git -C "$tmp/repo" rebase -i main >/dev/null 2>&1
expect skip DETACHED "a clean rebase stopped partway is left alone"
total=$((total + 1))
if [ "$(git -C "$tmp/repo" rev-parse feature)" = "$before_head" ] \
   && [ -d "$tmp/repo/.git/rebase-merge" ]; then
  echo "  ok: the rebase survived the hook intact"
else
  echo "  FAIL: the hook damaged an in-progress rebase"; failures=$((failures + 1))
fi
git -C "$tmp/repo" rebase --abort >/dev/null 2>&1

# A conflicted merge leaves HEAD on the branch, so the guard already returns ok — but
# the marker check must not turn that into a skip and start reporting the wrong verdict.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q main
printf 'diverged\n' > "$tmp/repo/tracked.txt"
git -C "$tmp/repo" commit -qam diverged
git -C "$tmp/repo" checkout -q feature
git -C "$tmp/repo" merge main >/dev/null 2>&1
expect skip feature "a conflicted merge is left alone"

echo "== no plan, or a plan for another branch: never act =="
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q main
rm -f "$tmp/repo/.claude/state/current-plan.json"
expect "" main "no plan state at all leaves HEAD alone"
expect_stdout empty "" "no plan emits no output"

rm -rf "$tmp/repo"; make_repo "$tmp/repo" ""
git -C "$tmp/repo" checkout -q main
expect "" main "a plan with no branch field leaves HEAD alone"

# An abandoned plan names a branch nobody is on. Restoring TO it would drag the session
# onto branch work it is not doing — the opposite of the bug this guards. Asserting `skip`
# rather than a failed restore is the point: the hook must decline because the branch was
# never adopted, NOT merely because the checkout happened to fail.
rm -rf "$tmp/repo"; make_repo "$tmp/repo" "some-other-branch"
git -C "$tmp/repo" checkout -q main
expect skip main "a plan naming a nonexistent branch is declined, not attempted"

echo "== a stale plan for an EXISTING branch never adopted: never act =="
# The reported bug. A new session opens on main; a plan file nobody deleted names feature,
# which exists and is checkable-out. The old guard read that mismatch as drift and dragged
# the session onto feature. Nothing here was ever adopted, so nothing is restored.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q main
expect skip main "a stale plan does not hijack a session that opened on main"
expect_stdout empty "" "a never-adopted plan emits no output"

# And it must not fight the user. Asking to switch back to main, repeatedly, has to work:
# each run is a fresh mismatch and each must be declined the same way.
expect skip main "asking for main a second time still leaves HEAD on main"
expect skip main "asking for main a third time still leaves HEAD on main"

echo "== adoption is observed, and a new plan branch invalidates the old latch =="
# Landing on the branch is what licenses future restores; the hook writes the latch itself.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
expect ok feature "sitting on the plan branch records the adoption"
total=$((total + 1))
if [ "$(cat "$tmp/repo/.claude/state/branch-adopted" 2>/dev/null)" = "feature" ]; then
  echo "  ok: the latch names the adopted branch"
else
  echo "  FAIL: the latch was not written on adoption"; failures=$((failures + 1))
fi
# Having adopted it, drift off it is now a real restore.
git -C "$tmp/repo" checkout -q main
expect restored feature "drift after adoption is restored"

# A latch left by a previous plan must not authorize the next one's branch.
rm -rf "$tmp/repo"; make_repo "$tmp/repo" "third-branch"
git -C "$tmp/repo" branch third-branch
adopt "$tmp/repo" "feature"
git -C "$tmp/repo" checkout -q main
expect skip main "a latch from a previous plan does not license a new branch"

echo "== a paused plan is a deliberate step away =="
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q main
printf '{"branch": "feature", "paused": true, "phases": []}\n' \
  > "$tmp/repo/.claude/state/current-plan.json"
expect "" main "paused plan leaves HEAD alone"
expect_stdout empty "" "paused plan emits no output"

echo "== malformed state never derails the turn =="
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
git -C "$tmp/repo" checkout -q main
printf 'not json at all\n' > "$tmp/repo/.claude/state/current-plan.json"
expect "" main "unparseable state is ignored"
expect_stdout empty "" "unparseable state emits no output"

echo "== outside a git repo, do nothing =="
# show-current fails rather than printing empty. Trusting the output alone would read
# that failure as a detached HEAD and try to check out a branch in a non-repo.
rm -rf "$tmp/repo"; mkdir -p "$tmp/repo/.claude/state"
printf '{"branch": "feature", "phases": []}\n' > "$tmp/repo/.claude/state/current-plan.json"
total=$((total + 1))
if [ "$(run_hook "$tmp/repo")" = "skip" ]; then
  echo "  ok: a non-repo is skipped, not treated as detached"
else
  echo "  FAIL: a non-repo was not skipped"; failures=$((failures + 1))
fi
expect_stdout empty "" "a non-repo emits no output"

echo "== the hook is dispatched even when it decides not to act =="
# A drift with no log line means the harness never ran the hook; a line with no restore
# means it ran and chose not to. Different bugs, and only the log separates them.
rm -rf "$tmp/repo"; make_repo "$tmp/repo"
run_hook "$tmp/repo" >/dev/null
total=$((total + 1))
if grep -q 'invoked branch-guard' "$tmp/repo/.claude/state/hook-invocations.log" 2>/dev/null; then
  echo "  ok: a no-op still logs that the hook was invoked"
else
  echo "  FAIL: a no-op left no invocation line"; failures=$((failures + 1))
fi

printf '\npassed=%d failed=%d\n' "$((total - failures))" "$failures"
if [ "$failures" -eq 0 ]; then
  echo "OK: protect-plan-branch restores a moved HEAD and never touches a correct one."
  exit 0
fi
echo "FAIL: protect-plan-branch self-test found $failures problem(s)."
exit 1
