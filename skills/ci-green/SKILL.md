---
name: ci-green
description: Monitor a PR's CI run and review feedback until every job passes and no unaddressed comments remain, root-causing each failure in an isolated subagent and propagating fix patterns across the codebase.
argument-hint: [PR number, defaults to the current branch's PR]
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

Drive PR $ARGUMENTS to fully green with no outstanding feedback.

Set `"stage": "ci-green"` and `"pr"` to the PR number in `.claude/state/current-plan.json`
now, and update `stage_step` on entering each step below. `/deliver`'s Step 0 resumes from
those; recording the PR number saves a resumed session re-deriving it, and distinguishes a
branch awaiting CI from one still unpushed.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` for this project's repo slug, result
artifact, and failure shapes.

## Step 1 — Arm the monitor, then stop talking

Start monitoring the CI run. Once a background monitor is armed, **say nothing until it
reports an actual event.** No "I'll wait for the next notification", no "still running", no
`sleep` loops, no polling status checks. The monitor pushes notifications on its own;
narrating the wait is pure noise.

If there is genuinely other useful work available — reading existing PR feedback,
investigating a doc gap — do that work instead of narrating.

## Step 2 — Distinguish hung from running

`Waiting for status to be reported` on a required check is not "still running". It means no
CI run is attached to the current HEAD commit — commonly a `[skip ci]` commit becoming HEAD
with no follow-up trigger. Before forming any opinion about CI state, check all three:

```bash
gh pr checks <pr>
gh run list --branch <branch>
git log origin/<branch> --oneline -5
```

A workflow `concurrency` block cancels an in-progress run when a new commit arrives on the
same ref, so a *cancelled* run is usually your own newer push superseding it — not a failure.
Confirm which commit each run is attached to before treating a cancellation as something to
investigate.

If Rob says CI is stuck or something is broken, investigate first and report what you find.
Never lead with reassurance. He has been right and the tooling wrong on this more than once.

## Step 3 — Handle each failure

For every failing job:

1. **Retrieve the real evidence.** `gh run view --log-failed`, or the uploaded result
   artifact named in `{{ci_results_artifact}}`. Never a console summary, never an exit code:
   an exit status routinely conflates a build failure with a test failure, and console output
   truncates.

   Where the artifact name carries both the run id and the attempt, use both: re-running only
   the failed job keeps the run number, so attempt-keying is what stops a re-run from reading
   the previous attempt's results. `gh run view <run-id> --json` lists the exact name if the
   attempt is not to hand.

   Read the counts with `{{results_read_command}}`.

2. **Root-cause it**, under `{{failure_policy_gate}}`'s failure policy — it governs CI jobs
   as much as local runs. No `paused` declaration is needed for the routine loop here;
   declare one only when ending a turn to ask Rob something.

   The failure shapes worth distinguishing on sight are in `{{mechanics_gate_pre_push}}`.
   Two generalize: a lint job that fails where the local run passed usually means CI runs at
   a stricter setting — fix the warning, never silence the rule, because those entries are
   deliberate choices and slipping one in to clear a build makes the file untrustworthy. And
   a test that fails in CI but passes locally is first an environment question: check whether
   it depends on a machine detail the two sides resolve differently.

3. **Write the fix** using the industry-standard pattern for the failure mode.
4. **Verify it in an isolated subagent before committing.** Launch `ci-failure-adversary`
   with only the failure evidence and the git ref of the fix — no explanation of your
   reasoning, no argument for why the fix is correct. It decides whether the fix addresses
   the root cause and whether the same root cause exists elsewhere in the codebase.
5. **Act on its verdict.** `SYMPTOM ONLY` or `UNVERIFIED` means the fix is not done. Fix
   every additional site it reports as a live defect in this same commit.
6. **Run the full Definition of Done, then commit.**
7. **Push per `${CLAUDE_PLUGIN_ROOT}/gates/pre-push.md`** — including its step 1 rebase onto
   the parent branch. An open PR is exactly where the parent drifts:
   `{{parent_branch_default}}` moves while the run is red, and a fix pushed onto a stale base
   can go green locally and stay red in CI against the merged result. Rebasing rewrites the
   branch, so this push is `--force-with-lease`.

   If the push gate itself fails on the way out, follow the post-failure procedure in
   `{{mechanics_gate_pre_push}}`: fix, re-verify what the fix affects, then push under that
   procedure's terms. A rebase onto a moved parent voids the allowance — the prior run no
   longer describes the tree, so the gate runs in full again.

If a fix touched code an expensive tier covers, validate narrowly — run only what the fix
affects, once. Do not re-run the whole suite to check a narrow fix.

## Step 4 — PR review feedback

Fetch from **both** endpoints. A review's main body is posted as an issue comment, so
checking only the pulls endpoint misses all the prose feedback:

```bash
gh api repos/{{repo_slug}}/pulls/<pr>/comments    # inline diff comments
gh api repos/{{repo_slug}}/issues/<pr>/comments   # top-level review body
```

Then, in this order:

1. **Fix the code first.** Never reply to a comment before the fix exists. Each fix goes
   through `ci-failure-adversary` the same way a CI failure does — root cause, pattern
   spread, then commit. Replying "good catch, filed as <ticket>" is a deferral: it needs the
   procedure in `deliver`'s invariants first — `commit-adversary` on the benign claim, then
   Rob's explicit agreement — before any ticket exists to cite.
2. **Reply to every inline thread**, naming what changed and in which commit:
   ```bash
   gh api repos/{{repo_slug}}/pulls/<pr>/comments/<id>/replies \
     --method POST -f body="Fixed in commit <sha>. <one-line explanation>."
   ```
   Replies to Greptile comments start with `@greptile:` followed by a space.
3. **Reply to the main PR summary comment** with a summary of all changes made, via the
   `issues/<pr>/comments` endpoint. Skip it only when every finding was handled inline and a
   summary would restate them verbatim.

Never run a fresh `/code-review` when asked to address existing feedback.

## Step 5 — Loop

Push, re-arm the monitor, stay silent. Repeat steps 2–4 until every check passes and no
comment is unaddressed.

Report at the end of each iteration, not only when the loop exits — an iteration is a
boundary like a phase, and a run that goes quiet for four pushes is one nobody can follow.
Per iteration: which checks went green and which are still red, the commits added, the files
they touched, how long the iteration took, and one line per issue fixed with its root cause
and the sites the pattern-spread grep covered.

When the loop exits, report the full status: final check status, every commit added across
all iterations, all files changed, total wall-clock, the acceptance criteria table with
evidence — CI passing is evidence for an AC that a test covers, and now is when it becomes
available — and, still listed as outstanding, any AC awaiting out-of-band verification. **CI
going green does not close those.**

Then, and only here, **the process-improvement list for the whole delivery.** Read
`friction[]` from `.claude/state/current-plan.json` and report every item recorded by every
stage — deduplicated, each with the file it belongs in, the exact proposed wording, what it
displaces, and the cap check from `deliver`'s line-budget table. Keep each item's origins
rather than collapsing them: "seen in Phase 2, Phase 5, branch-review" is a different signal
from one sighting, and it is what tells Rob which rules actually cost time.

Then **stop and ask** before applying any of them. Do not edit `CLAUDE.md`, a gate, a skill,
or a memory file on your own initiative; a config file that grows on every run stops being
read. An item Rob declines is dropped, not re-proposed next run.

Report `none` when the run genuinely recorded no friction. A clean run is a real outcome,
and manufacturing an item to fill the section is how a config file accumulates rules nobody
needed.

**Report this before Step 6 deletes the state file.** The list lives in the file being
removed, and a report written after the delete has nothing to read.

## Step 6 — Clean up the run's scratch files

**Only once the run is genuinely finished** — every check green, no unaddressed comment, the
final report written. Report the deletions as part of that report.

```bash
rm -f .claude/state/current-plan.json .claude/state/blocked-*
rm -f docs/plans/<primary-ticket>*.md
```

Both are working state for a delivery in flight, not artifacts of it: `docs/plans/` is
gitignored, and the PR body plus the commits carry everything a reader needs afterward. Left
behind, the state file is worse than clutter — `/deliver`'s Step 0 finds it and resumes a run
that already shipped, and the branch guard keeps dragging HEAD back to a branch nobody is
working on.

Named files, not `find .claude/state -type f -delete`: that also removes
`hook-invocations.log` — the only diagnostic trail either hook leaves, carrying both the Stop
hook's verdicts and the branch guard's — at the end of exactly the run whose hook behavior
someone would want to inspect.

The glob catches the plan and anything written alongside it — handoff notes, scratch drafts.
Delete nothing outside `docs/plans/` and `.claude/state/`, and never a tracked file:
`git status` must be clean afterward, exactly as it was before.

If the PR is not merged yet, that is fine — the branch and the PR are the record from here
on. But if anything is still red or unaddressed, the run has not finished and nothing gets
deleted. **An outstanding out-of-band verification does not block cleanup**: it is Rob's to
run, it is recorded in the PR body, and holding the state file open for it would strand the
branch guard indefinitely.
