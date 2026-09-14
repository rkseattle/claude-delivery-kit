---
name: ship-pr
description: Run the full pre-push gate, resolve any out-of-band verification the diff needs, push the branch, open the PR, and transition the covered Jira tickets to In Review.
argument-hint: <TICKET-N> [TICKET-N ...]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

Ship the branch covering: $ARGUMENTS

Run only after `/branch-review` has returned APPROVE.

Set `"stage": "ship-pr"` in `.claude/state/current-plan.json` now, and update `stage_step`
on entering each step below. `/deliver`'s Step 0 resumes from those — and Step 4's push is
the point where a resumed run must know whether the PR already exists.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` for this project's push procedure and
verification tiers.

## Step 1 — Rebase onto the parent, then local CI equivalence

Read `${CLAUDE_PLUGIN_ROOT}/gates/pre-push.md` and `{{mechanics_gate_pre_push}}`, and run
the checklist in order. Everything CI will run, runs here first — and possibly more, where
the project's local gate covers something CI does not.

The checklist opens with a rebase onto the parent branch, and it is first for a reason: CI
tests your branch merged with the parent, so a gate run on the pre-rebase tree is not
testing what CI will test. Rebase before Step 2 as well — pulling in parent commits after a
passing verification invalidates it, and the expensive tiers are expensive to repeat.

## Step 2 — Resolve the verification the diff needs

**This step is where projects differ most, and the project's answer is authoritative.**
`{{verification_step_file}}` says what this diff needs beyond the pre-push checklist, and
`{{verification_tiers}}` names the tiers an AC can be verified by. Read it and answer it
explicitly here; do not skip past it because everything is green.

Two shapes recur, and the project file says which applies:

**An automated tier the push itself runs.** Where a push hook resolves the diff to affected
tests and attests they executed against this HEAD, do not run that suite by hand and then
bypass the hook. The gate's bypass section says why, and its cadence rules still apply. Read
counts from `{{results_file}}`, never the console and never the exit code. If output
truncates, read the file — do not re-run.

**A tier no automation can reach.** Where the suite is structurally silent on the thing that
changed — behavior only real hardware, a real integration, or a human can observe — you
cannot run it yourself. So:

1. Confirm the branch builds for the target the verification needs, with
   `{{release_build_command}}` where the project defines one. A branch that cannot build for
   that target is not ready to hand over.
2. **Hand Rob the charter**: the items from `{{verification_step_file}}`, narrowed to the
   ones this diff can affect, with one line each on what a failure would look like. Not
   "please test it" — the specific things to watch.
3. **Ask whether to push now or wait for the session.** Both are legitimate: an early PR
   makes CI run and the diff reviewable, and the outcome lands in the PR afterward.
   Recommend pushing now unless the diff is one where a failure would rewrite the approach
   rather than adjust it.

Whichever he chooses, the PR body records those ACs as outstanding until the verification
reports. Never mark such an AC met on the strength of a green automated run.

If the verification fails, root-cause and fix, then re-verify **only what the fix affects**,
per `{{failure_policy_gate}}`. If you cannot find the root cause, declare the stop per
`deliver`'s invariants and ask.

## Step 3 — Clean the working tree

`git status`. Restore or remove every tracked file with local modifications that is not part
of the intended commit set — result bundles, generated outputs, editor droppings. Pushing
these contaminates history. When unsure whether a change was intentional, ask — never
silently include or silently drop it.

## Step 4 — Push and open the PR

Where the push runs an expensive gate inside it, **detach it**: a foreground call cannot
outlive its tool timeout and a session-scoped background task dies with the session, and
both kill the run mid-suite. `{{push_command}}` is the project's exact invocation.

```bash
nohup {{push_command}} > /tmp/push.log 2>&1 &
```

Then arm a `Monitor` that watches for the remote branch appearing, and stay quiet until it
reports. Where the push is fast, run it in the foreground and skip the monitor.

`--force-with-lease` because Step 1's rebase rewrote the branch, so a branch already pushed
will reject a fast-forward push. Never bare `--force`: `--force-with-lease` aborts when the
remote moved under you instead of overwriting whatever landed there.

If the lease check rejects the push, the remote has commits your local copy does not —
someone else pushed, or an earlier run of this skill did. Do not re-force past it. Fetch,
look at what is there, and reconcile.

**A killed run is not a failed run** — no result file, no verdict, so the never-rerun rule
does not govern it. Confirm HEAD is unchanged, then start it again.

**Do not bypass the gate on the first push.** This push is where it runs. Expect it to take
a while, and let it. The bypass exists for the documented post-failure case in
`{{mechanics_gate_pre_push}}`, not for a run you would rather not sit through.

```bash
gh pr create --title "<ALL ticket IDs> — <summary>" --body "<body>"
```

Once the PR exists, record it in `.claude/state/current-plan.json` — `"pr"` set to its
number, `"stage": "ci-green"` — and **leave the state file in place.** The work is not
finished until CI is green, and `/deliver`'s Step 0 resumes stage 5 from these fields: a run
interrupted between the push and a green build must know the PR already exists, or it
re-enters this stage and pushes again. `/ci-green` deletes the file when the run genuinely
ends.

Title lists every covered ticket ID in full — never abbreviated, never partial.

Body:

- What ships, in prose
- Ticket links
- Per-ticket acceptance criteria and how each is satisfied
- **Testing performed**, split by tier per `{{verification_tiers}}`, because the tiers are
  not interchangeable: the counts read from the result file for each automated tier, and for
  any out-of-band tier either the outcome per item or "outstanding: <items>" when it has not
  happened yet
- Migrations, feature flags, persisted-state changes, and anything a user upgrading will
  notice
- Anything deliberately deferred, with the reason. Every entry here must already have
  cleared the deferral procedure in `deliver`'s invariants — `commit-adversary` on the
  benign claim, then Rob's explicit agreement. The PR body records a decision already made;
  it is not where a deferral gets decided, and "listed in the PR" is not a substitute for
  fixing.

## Step 5 — Jira

Transition every covered ticket to **In Review**. Look up the issue's available transitions
via the Atlassian MCP first and use the ID it returns — never guess one.

## Step 6 — Hand off

Report the PR URL and the ticket transitions, then the stage status in the same shape every
phase used:

- **Stage table** — which `deliver` stages are complete and which remain, with the
  wall-clock each took.
- **Files** — everything on the branch, `git diff --stat {{parent_branch_default}}...HEAD`,
  plus anything this stage changed on its own (a restored artifact, a regenerated baseline).
- **Acceptance criteria** — the full table with evidence, with any row awaiting out-of-band
  verification called out separately as outstanding. Every AC met, or an explicit statement
  of which are not and why the PR opens anyway.
Friction and citations from this stage are recorded to `friction[]` and `citations[]`, not
reported here — `/ci-green` reports each list once for the whole delivery.

Then run `/ci-green` to watch the run through to completion.
