#!/usr/bin/env bash
# PostToolUse(Bash) hook: put HEAD back on the branch an active plan is being
# delivered on, whenever a command moved it off.
#
# A review subagent shares the working tree with the session that spawned it. One
# `git checkout main` to "look at" a ref leaves the parent on the wrong branch, and its
# next commit lands somewhere nobody intended. That happened once; this restores the
# branch and says so, in the same turn, before the next commit can land.
#
# This runs AFTER the command. The predecessor ran before it and had to answer "would
# this move HEAD?" from the command text — which meant reimplementing the shell's
# reading of sudo, env -S, xargs, find -exec, git submodule foreach, quoting and line
# continuations. Four review rounds found thirteen bypasses in that parser and each
# round found more; because the guard failed open, every gap was silent. This asks git
# where HEAD actually is instead, so no command spelling can hide from it and there is
# nothing left to bypass. The cost is that the checkout runs before it is undone.
#
# Decides from typed state only — the branch named in current-plan.json and the branch
# git reports — never from the prose of the command. Every error exits quietly: a hook
# that derails a turn on its own bug is worse than no hook.
#
# A mismatch between HEAD and the plan branch has two causes that look identical in a
# single snapshot: DRIFT (the session was on the branch and a command moved it off) and
# NEVER-ADOPTED (the session never went there — a new session on main with a stale plan
# file nothing ever deleted). Restoring the second hijacks the session onto abandoned
# work, and re-hijacks it every time the user asks to switch back, which reads as the
# guard refusing a direct instruction.
#
# So the restore is latched on adoption: .claude/state/branch-adopted records the branch
# this hook has actually SEEN HEAD sitting on. Only a mismatch against a matching latch
# is drift. The latch stores the branch name rather than existing bare, so a plan that
# names a new branch invalidates the old latch by itself — no cleanup step to forget.
#
# The latch fails open: lose the state directory mid-plan and the guard stays quiet until
# HEAD next lands on the branch. That is the deliberate trade — an unprotected window is
# recoverable, a session dragged onto the wrong branch is the bug being fixed.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "${1:-}" = "--self-test" ] && exec bash "$HOOK_DIR/protect-plan-branch.self-test.sh" "${BASH_SOURCE[0]}"

# No stdout at all is a valid "nothing to say" for PostToolUse.
quiet() { exit 0; }

# Records that the harness actually ran this script, mirroring the Stop hook's log. A
# drift with no line here means the hook was never dispatched; a line with no matching
# restore means it ran and decided not to act. Nothing else tells those apart, and they
# have different fixes. Never fails the hook: a log that breaks the guard is worse than
# no log.
log_invocation() {
  local dir="$1/.claude/state" logfile
  logfile="$dir/hook-invocations.log"
  [ -d "$dir" ] || return 0
  if [ -f "$logfile" ] && [ "$(wc -l < "$logfile" 2>/dev/null || echo 0)" -gt 500 ]; then
    tail -n 200 "$logfile" > "$logfile.tmp" 2>/dev/null && mv "$logfile.tmp" "$logfile" 2>/dev/null
  fi
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$2" >> "$logfile" 2>/dev/null || true
}

command -v jq >/dev/null 2>&1 || quiet
input=$(cat 2>/dev/null) || quiet
[ -n "$input" ] || quiet

# cwd is not guaranteed to be the repo root, and a state path that misses silently
# disables the hook.
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // "."' <<<"$input" 2>/dev/null)}"
state="$root/.claude/state/current-plan.json"

# No active plan means no branch to protect. Checked before logging so an idle repo
# does not fill the log with lines about a plan that does not exist.
[ -f "$state" ] || quiet

want_branch=$(jq -r '.branch // ""' "$state" 2>/dev/null) || quiet
[ -n "$want_branch" ] || quiet

# A paused plan is one the session deliberately stepped away from; honoring the pause
# here matches the Stop hook, which reads the same field.
[ "$(jq -r '.paused // false' "$state" 2>/dev/null)" = "true" ] && quiet

log_invocation "$root" "invoked branch-guard"

# Empty means detached HEAD, which is off the branch just as surely as another ref.
# A failure here (not a git repo, git missing) is indistinguishable from detached by
# output alone, so the exit status decides: only a SUCCESSFUL read is trusted.
if ! actual=$(git -C "$root" branch --show-current 2>/dev/null); then
  log_invocation "$root" "verdict=skip git-unreadable"
  quiet
fi

# A rebase, merge, cherry-pick, revert or bisect OWNS HEAD for its duration — a rebase
# detaches it by design and only reattaches on completion. Restoring during one is not a
# repair, it is destruction: `git checkout <branch>` mid-rebase resets the branch to its
# pre-rebase commit, discarding every commit already replayed, and leaves the operation's
# state directory behind so `--continue` then fails on empty cherry-picks. That is
# unrecoverable, and pre-push.md makes a rebase mandatory before every push, so this is
# the guard's own workflow rather than an edge case.
#
# Detected from the state files git itself writes, not from the command text — the same
# reason the rest of this hook reads git instead of parsing what ran.
git_dir=$(git -C "$root" rev-parse --git-dir 2>/dev/null) || git_dir=""
if [ -n "$git_dir" ]; then
  case "$git_dir" in /*) ;; *) git_dir="$root/$git_dir" ;; esac
  for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    if [ -e "$git_dir/$marker" ]; then
      log_invocation "$root" "verdict=skip in-progress=$marker"
      quiet
    fi
  done
fi

latch="$root/.claude/state/branch-adopted"

# HEAD is where the plan wants it. This is the ONLY thing that ever writes the latch:
# adoption is observed, never assumed, so a plan file alone can never authorize a restore.
if [ "$actual" = "$want_branch" ]; then
  if [ -d "$(dirname "$latch")" ]; then
    printf '%s\n' "$want_branch" > "$latch" 2>/dev/null || true
  fi
  log_invocation "$root" "verdict=ok on=$want_branch"
  quiet
fi

# HEAD is elsewhere. Whether that is drift or a session that was never on the branch is
# decided by the latch, and a latch naming a DIFFERENT branch is not adoption of this one:
# it belongs to a previous plan, so it reads as never-adopted rather than as drift.
adopted=""
[ -f "$latch" ] && IFS= read -r adopted < "$latch" 2>/dev/null
if [ "$adopted" != "$want_branch" ]; then
  log_invocation "$root" "verdict=skip not-adopted want=$want_branch on=${actual:-DETACHED}"
  quiet
fi

# HEAD moved. Put it back.
#
# git refuses a checkout that would overwrite uncommitted tracked changes, so this can
# fail — and a restore reported as done when it did not happen is the one outcome worse
# than no restore. The exit status, not the message, decides which is reported.
if restore_error=$(git -C "$root" checkout "$want_branch" 2>&1); then
  outcome="restored"
else
  outcome="failed"
fi

display_actual="${actual:-a detached HEAD}"

if [ "$outcome" = "restored" ]; then
  log_invocation "$root" "verdict=restored from=${actual:-DETACHED} to=$want_branch"
  message="branch-guard: HEAD had moved to $display_actual; restored to '$want_branch'."
  context="The command just run moved HEAD off '$want_branch', the branch the active plan
in .claude/state/current-plan.json is being delivered on. HEAD was on $display_actual and
has been checked out back to '$want_branch' automatically — no action is needed, but do
not repeat the command.

Read another ref without moving HEAD:
  git show <ref>:<path>
  git diff <base>...<branch>
  git log <base>..<branch>
  git grep <pattern> <ref> -- <path>

If you genuinely need to switch branches, clear or pause the plan state first."
else
  log_invocation "$root" "verdict=restore-failed from=${actual:-DETACHED} to=$want_branch"
  message="branch-guard: HEAD is on $display_actual, not '$want_branch', and the restore failed."
  context="The command just run moved HEAD off '$want_branch', the branch the active plan
in .claude/state/current-plan.json is being delivered on. HEAD is now on $display_actual
and the automatic restore FAILED, so the working tree is still on the wrong branch.
Do not commit until this is resolved — a commit now lands on the wrong branch.

git said:
$restore_error

Usually this means uncommitted changes would be overwritten by the switch. Resolve them
(commit them to the right branch, or stash them), then run:
  git checkout $want_branch"
fi

jq -n --arg m "$message" --arg c "$context" '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: $c,
    systemMessage: $m
  }
}'
