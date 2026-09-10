# Pre-push and pre-PR gate

The commands, job names and thresholds are in `{{mechanics_gate_pre_push}}` — this file is
the policy, that file is what to run. Read both.

## Pre-push checklist

In order, all green, before every `git push`:

1. **Rebase onto the parent branch.** Required before every push, not only the first.

   ```bash
   git fetch origin
   git rebase origin/<parent>   # {{parent_branch_default}} unless cut from another branch
   ```

   The parent is whatever this branch was cut from — a stacked branch rebases onto its own
   parent, not past it. `git merge-base` against the candidate confirms it when you are
   unsure: `merge-base HEAD origin/<parent>` equal to `origin/<parent>` means the branch
   already sits directly on it and the rebase would replay nothing, which satisfies this
   step.

   **This is step 1 because every step below it certifies a specific tree.** A rebase
   rewrites the branch onto commits that were not present when the gates ran, so a gate run
   before the rebase describes code you are no longer pushing — the exact mechanism behind
   "green locally, red in CI", since CI tests the merged result and you tested the unmerged
   one. If you rebase after running any gate step, every step below runs again.

   **Resolve conflicts, never paper over them.** A conflict means someone changed what you
   changed. Read both sides and reconcile the intent — a wholesale `--ours`/`--theirs`, or
   `git rebase --skip`, silently drops one side's work. If the resolution is not obvious,
   stop and ask rather than guessing.

   **Do not substitute a merge.** Merging the parent also integrates it, but puts a merge
   commit in the branch's history, which is not what this gate asks for.

   After the rebase the branch has diverged from its remote, so the push is
   `--force-with-lease`. Never bare `--force`: `--force-with-lease` refuses when the remote
   moved under you, which is precisely the case where a blind force destroys someone else's
   commits.

2. **Format check and lint**, at CI's strictness.
3. **Typecheck or compile**, where the project has a step distinct from its tests.
4. **The unit suite**, at the scope `{{unit_test_scope}}` names. That key is the project's
   answer to a real trade: running the whole target matches what CI runs and cannot be
   wrong about which subset mattered, while a scoped run is cheaper on a slow suite. The
   project states which it takes and why.

   **Check the executed count, not just the failure count.** Zero failures out of forty
   executed is not a pass of an eight-hundred-test suite — it is a run that died early.
   Compare the total against the previous run's before believing a green verdict.

5. **Dependency audit**, where the project has dependencies — always, never conditional on
   whether they changed. Advisories are published against versions you already have: a
   lockfile clean yesterday fails today because the advisory database moved, not because
   anything in the repo did. The bar is zero, with no allowlist.
6. **A production-configuration build**, where the project has one distinct from its test
   build. Optimization and stripped debug-only paths mean a production-only break is
   invisible until this point.
7. **The verification tier the diff needs**, per `{{verification_step_file}}`. Where a push
   hook runs an expensive suite, this is where it happens; where the tier is one no
   automation can reach, this is where the charter is handed over. Answer it explicitly —
   do not skip past it because everything else is green.

   **Detach the push** when the gate runs inside it. A foreground call cannot outlive its
   tool timeout and a session-scoped background task dies with the session; both kill the
   run mid-suite and leave no result file.

8. **`git status`** — scan for tracked files with local modifications that are **not** part
   of the intended commit set. Restore stray artifacts and generated outputs. When unsure
   whether a change was intentional, ask — never silently include or silently drop it.

Lint and typecheck are separate gates from tests: a branch that fails either fails CI even
when every test passes locally.

Steps 2–8 all describe the post-rebase tree. If anything sends you back to step 1 — a late
conflict, a parent that moved while the suite was running — the steps after it are stale and
run again.

## Bypassing a push gate

A bypass exists for the case where the gate cannot do its job — its infrastructure is down,
its inputs are unusable, or you have already run it by hand for a reason you can state. It
is not the normal path, and reaching for it because the gate is slow is how a branch reaches
CI unverified.

**Prefer a bypass that leaves a record over one that is silent.** Where the project's gate
has its own escape hatch, use it: it logs the use with a timestamp and the branch. A blanket
`--no-verify` reaches the same end silently and leaves nothing to audit. Use `--no-verify`
only when the gate itself is broken in a way its own switch cannot route around.

If the reason is "I already ran it by hand", all of these must hold:

1. **Every part of the suite ran**, not one half of a partitioned run.
2. **Zero failures, read from the result file** rather than from a console summary.
3. **HEAD is unchanged from what that run executed against.** Any commit, amend, or rebase
   afterwards voids the result and the gate restarts from step 1. Confirm it; do not assume.
4. **The cheap gates still run.** A bypass skips one leg, not the checklist. Lint,
   typecheck, unit tests and the audit are seconds against a long suite, and the audit in
   particular fails on advisories published against a lockfile nobody touched.

**Never bypass to get around a failure, a flake, or a run you would rather not sit
through.**

**A run that aborted before executing anything produced no verdict at all** — a killed
process, a stale environment, a stack built at the wrong commit. There is no result to
preserve and nothing to bypass: fix the environment and let the gate run normally.

### After the gate's own run fails

Whether a fix commit restarts the gate from step 1 is `{{post_fix_verification_scope}}`, and
the project's answer turns on whether it can determine what a fix affects. A project whose
selector resolves a diff to the affected tests can re-run that set and have a real verdict
on the new tree. A project without one has no such answer, and its only honest
re-verification is the whole suite — which is cheap enough there to be no hardship.

Taken literally, condition 3 means a full suite per fix. On a branch with three failures
that is hours of re-running tests that already told you what they knew, and that cost is
how a real failure gets rationalised as a flake: confirming it honestly becomes more
expensive than pretending it was noise.

So where the project grants the exception, its bounds are not negotiable:

- **Root-cause and fix first.** No failure is dismissed as a flake, pre-existing, or
  unrelated, and a rerun that passes is not a resolution.
- **Re-run what the fix affects**, once, against the fixed tree — asking the selector rather
  than assuming the failed set is the whole set. A fix in a test's own logic usually re-runs
  just that test; a fix in shared code pulls in previously-passing tests the failed set does
  not name, and those are exactly where a regression in the fix would land.
- **The sole delta from the failed run is the fix.** Add a feature, touch unrelated code, or
  rebase onto a moved parent, and the prior run no longer describes the tree — restart at
  step 1.
- **No second bypass for the same failure.** If the targeted run fails again, you have not
  fixed it.

What this gives up, in every project: a hand-run proves those tests passed, not that they
passed against this commit. That part is on you, which is why "the sole delta is the fix" is
the bound to be strict about rather than eyeball.

## What CI runs, and what it does not

`{{mechanics_gate_pre_push}}` lists the jobs and which local step is each one's equivalent.
Two rules generalize:

**Name what CI does not cover.** Every project has a suite CI skips or a tier it cannot
reach. Those are yours, and a green CI run is not evidence for them.

**A single aggregating check is what makes path filtering safe.** Where CI skips jobs by
path filter, the required check must be one that always runs and treats a skipped job as
passing. A conditional job named directly as a required check blocks the PR forever, waiting
on a status a skipped job never reports.

**If your diff touches the hooks or the workflow, the unit suite is not enough** — run both
hook self-tests locally:

```bash
bash "$CLAUDE_PLUGIN_ROOT/hooks/block-false-stop.sh" --self-test
bash "$CLAUDE_PLUGIN_ROOT/hooks/protect-plan-branch.sh" --self-test
```

## Pre-PR self-review

- [ ] Dead code removed — unused imports, variables, properties, localization keys
- [ ] Every user-facing string localized, present in every locale
- [ ] A programmatic test locator on new interactive elements
- [ ] Loading, error, and empty states handled for every async surface
- [ ] User docs updated for user-visible behavior
- [ ] No work-item ID in any source comment — they belong in the commit message and PR
      title only
- [ ] Every comment added explains why, within `CLAUDE.md`'s budget; none restates the code
      or narrates a review round
- [ ] Would pass a Greptile review

The project's own items are in `{{mechanics_gate_pre_push}}`.

## PR conventions

- Branch from `{{parent_branch_default}}` unless instructed otherwise.
- Rebase onto the parent before every push, per step 1 — including pushes that answer review
  feedback on an open PR. An open PR is exactly where the parent drifts.
- PR title lists **every** covered ticket ID in full. Never abbreviated, never partial.
- Reference the ticket number in every commit message, never in a code comment.
