---
name: branch-review
description: Run a cold, Greptile-style full review of every change on the current branch in an isolated subagent, then fix findings by root cause and propagate each fix pattern across the codebase.
argument-hint: [base-ref, defaults to the project's parent branch]
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

Full branch review. Base ref: $ARGUMENTS (default `{{parent_branch_default}}`).

Run this after every phase is committed and before `/ship-pr`.

Set `"stage": "branch-review"` in `.claude/state/current-plan.json` now, and update
`stage_step` on entering each step below. `/deliver`'s Step 0 resumes from those.

## Step 1 — Cold review

Launch the `greptile-reviewer` subagent.

**The delegation prompt contains only:** the branch name, the base ref, and the covering
ticket IDs. Nothing else — no summary of what the branch does, no note about which phases
were tricky, no "pay attention to X". The whole value of this pass is that the reviewer has
no implementation context. Anything you add erodes it.

## Step 2 — Fix by root cause, not by finding

For each BLOCKER and MAJOR, in order:

1. **Establish the root cause.** The reviewer names one; verify it against the code rather
   than accepting it. A finding is a symptom; the cause is what you fix.
2. **Grep for the same root cause across the whole repo** — not just the branch, not just
   the reported file. Same pattern, not same string. If the finding was a missing ownership
   clause, check every endpoint. If it was a missing cancellation on a replaced task, check
   every place work is assigned.
3. **Decide the scope of the fix.** Every live instance of the root cause gets fixed in this
   pass; excluding one requires `deliver`'s benign-in-context bar. State the exclusion in
   those terms or fix it.
4. **Fix using the industry-standard pattern, and name it before writing the fix** — the
   documented standard, framework convention, or known implementation it is an instance of.
   Not the minimal edit that clears the finding. Matching in-repo precedent is sufficient
   only where you can also say what that precedent is an instance of; one you cannot name
   externally is local invention, and a fix that matches it entrenches the thing the next
   round will find. Where the finding is itself against an in-repo pattern, the standard is
   what the fix conforms to — not the pattern. Record the name in the commit message and
   append it to `citations[]` in `.claude/state/current-plan.json`, per
   `${CLAUDE_PLUGIN_ROOT}/gates/status-report.md`.

MINOR findings: fix them. Defer only when the fix needs a decision you cannot make — a
product choice, a migration, a superseding ADR. Branch size is not such a decision: if the
branch has grown too large to review, that is a signal to have split it at plan time, not a
licence to leave a live defect in place now.

**Before deferring anything, and before creating any work item, follow the deferral
procedure in `deliver`'s invariants**: test the benign claim with `commit-adversary` (refs
only — file, line, root cause, your one-sentence claim), then ask Rob, then file. Filing a
ticket unprompted is the failure mode this guards against; it produces the feeling of having
handled the finding without handling it.

Work through findings in batches by root cause, not one commit per finding.

## Step 3 — Validate before reporting

Do not report a fix as complete on reasoning alone. Run the verification — the failing test,
the endpoint, the service logs, whatever settles it — and include the output. This has
repeatedly been the difference between "fixed" and "still broken when Rob tried it".

This comes before the re-review deliberately: a fix you have not verified is a fix the next
round will find, and spending a review round on it wastes the scarcest thing the reviewer
produces.

## Step 4 — Re-review

Once fixes are committed, re-run `greptile-reviewer` against the same base ref with the same
minimal prompt. Continue until the verdict is APPROVE, to a maximum of three rounds. If it
still requests changes after the third round, stop and bring the specific disagreement to
Rob rather than iterating further, declaring the stop per `deliver`'s invariants.

**Check what each round is about before starting the next**, per `deliver`'s revert rule.
Findings against code a previous round wrote — rather than against the branch's own work —
mean that fix was the wrong shape. Revert it and take a different approach; a third round
will not converge on a design that should not exist. `deliver`'s enforcement-machinery
invariant records what this failure mode has cost.

## Step 5 — Verify the acceptance criteria table

The reviewer returns an AC coverage table. Check each unmet or partially-met row yourself
against the ticket. Any AC not demonstrably satisfied by code plus a test is not done,
regardless of how the branch feels.

An AC whose `verified_by` names an out-of-band tier is not settled by this review either.
Carry it forward as outstanding rather than letting an APPROVE verdict imply it is covered.

## Gates

Every fix commit in this skill still runs the full Definition of Done in
`${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` and `{{mechanics_gate_dod}}`, including
the "Before `git add`" checks. Nothing about being in review mode relaxes the commit gates.

## Report at the end of the stage

Same shape as a phase report: which findings were fixed and which were argued down, the
files each fix touched, how long the stage took, and whether any finding moved an
acceptance criterion. Friction is recorded to `friction[]`, not reported here.

A review finding that a written rule would have prevented is worth reporting — it was caught
late, by an agent, on work already committed. But check which of the two it is before
proposing anything: a finding no rule covers, or a finding a rule already covered and the run
did not follow. The second is far more common, and its fix is never new text. It is moving
the existing rule to where the run was reading, or deleting a competing copy that said
something subtly different. Both of those shrink the corpus.

Propose new text only for the first kind, naming what it displaces per `deliver`'s
line-budget invariant. A guard, hook, or check script is never a review fix: propose it as a
phase under `deliver`'s enforcement-machinery invariant, with the invariant it would enforce
stated, and let it be written and reviewed on its own diff.
