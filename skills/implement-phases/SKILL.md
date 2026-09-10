---
name: implement-phases
description: Execute an approved phased plan — create the branch, transition Jira to In Progress, then implement, adversarially review, and commit each phase in turn without pausing between them.
argument-hint: <path-to-plan.md>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

Implement the approved plan at: $ARGUMENTS

Requires an approved plan. If no plan has been approved in this session, stop and run
`/plan-work` instead.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` first for this project's ticket prefix,
parent branch, and gate mechanics.

## Step 1 — Set up once

```bash
git checkout {{parent_branch_default}} && git pull
git checkout -b <ticket-slug>
```

Branch from `{{parent_branch_default}}` unless instructed otherwise. Then transition every
covered ticket to **In Progress**. Look up the issue's available transitions via the
Atlassian MCP first and use the ID it returns — never guess one.

Read `${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` and `{{mechanics_gate_dod}}` now.
They apply to every commit in this skill and do not need re-reading between phases.

Then write the phase list to `.claude/state/current-plan.json`, which is what the `Stop`
hook reads to tell an unfinished plan from a finished one, and what the branch guard reads
to put HEAD back on this branch whenever a command moves it off.

```json
{
  "branch": "<ticket-slug>",
  "plan": "docs/plans/<primary-ticket>.md",
  "tickets": ["{{ticket_prefix}}-N"],
  "stage": "implement-phases",
  "stage_step": "2a — implement, phase 1",
  "phases": [{ "name": "Phase 1 — <name>", "done": false }]
}
```

`stage` and `stage_step` are what `/deliver`'s Step 0 resumes from. Update `stage_step` at
the top of each step below — 2a, 2c, 2d — before doing the step, naming the phase it
belongs to. A session killed without warning leaves behind whatever was written last, so a
marker written on the way into a step survives the crash and one written on the way out
does not.

One entry per phase in the approved plan, all `done: false`. `branch` is the branch just
created, and the two hooks read that field in opposite directions:

- The **Stop hook** ignores a state file naming a branch that is not checked out, so
  abandoned work stops nagging once you switch away from it.
- The **branch guard** treats exactly that mismatch as its trigger: it puts HEAD back on
  `branch` after any command that moves it off. A stale state file does not go inert when
  you switch away — it drags HEAD back after every Bash command until the file is removed.

So a finished or abandoned run must have its state file deleted, not merely left behind on
a branch nobody is on.

`acceptance_criteria` is copied from the plan's **Acceptance criteria coverage** table —
one entry per row, keeping that table's `AC<n>` IDs so the plan, the state file, and every
status report name the same criterion. Copy the rows; do not re-derive them from the
tickets, which produces a second list free to drift from the one the plan was approved
against. Carry `verified_by` across: it is what stops an AC that only out-of-band
verification can settle being marked met by an automated test.

```json
"acceptance_criteria": [
  { "id": "AC1", "ticket": "{{ticket_prefix}}-N", "text": "<AC text>",
    "verified_by": "<tier>", "met": false, "evidence": "" }
]
```

If the field is absent — an older state file, or a plan predating this — rebuild it from
the plan's coverage table before the first phase report, assigning IDs in table order. Do
not paraphrase the text: an AC reworded into something easier to satisfy is how a run
reports green against criteria nobody agreed to. If the plan has no coverage table either,
say so and ask rather than writing the criteria yourself.

Each phase gains four more fields as it runs — `started_at`, `finished_at`, `commit`, and
`files`. They exist so duration and file lists are read back rather than recalled: a phase
spanning a compaction boundary is otherwise unreportable, and an estimated duration is
worse than none.

```json
{
  "name": "Phase 1 — <name>",
  "done": true,
  "started_at": "2026-09-02T15:12:04Z",
  "finished_at": "2026-09-02T15:53:41Z",
  "commit": "ab8c4cd",
  "files": ["<path>"]
}
```

Both timestamps come from `date -u '+%Y-%m-%dT%H:%M:%SZ'`, never from a timestamp in
context. `files` and `commit` come from `git show --stat --name-only` on the commit just
made — never from memory of what you edited, which misses build manifests, generated
files, and whatever a lint autofix touched.

Set `"paused": true` before ending a turn deliberately, per `deliver`'s invariants, and
**remove it as the first action of the turn that resumes** — left set, it disables both
hooks for every remaining phase.

If work is abandoned before `/ship-pr`, clear the state with
`rm -f .claude/state/current-plan.json .claude/state/blocked-*` and delete the plan from
`docs/plans/`. Use those named paths, not `find .claude/state -type f -delete`, which also
removes `hook-invocations.log` — the only diagnostic trail either hook leaves, carrying
both the Stop hook's verdicts and the branch guard's (`verdict=ok`, `verdict=restored`,
`verdict=skip in-progress=<marker>`). A completed run is cleaned up by `/ci-green`'s Step 6
instead, not before, because every stage after this one resumes from this file.

## Step 2 — Run all phases straight through

Once the plan is approved, run every phase to completion **without stopping to ask whether
to proceed to the next one**. The phased structure exists for commit granularity and
reviewability, not as approval gates. Report progress and blockers as they occur and keep
going.

Stop mid-plan only for a genuine decision: ambiguous scope the plan did not settle, a
judgment call with real tradeoffs, or a discovery that invalidates the plan. "Phase N is
done" is not such a decision.

For each phase:

### 2a. Implement

Record `started_at` for this phase before the first edit — `date -u '+%Y-%m-%dT%H:%M:%SZ'`.

While the phase runs, keep a note of anything that cost real time and was avoidable: a gate
that failed for a reason a rule could have prevented, an adversarial round spent on
something already written down, a convention discovered by being corrected rather than by
reading it. Record it to `friction[]` the moment you notice it, per
`${CLAUDE_PLUGIN_ROOT}/gates/status-report.md` — noticing afterward does not work, because
by then the cost is invisible.

Industry-standard patterns only, per `deliver`'s invariant. Put the reason for any departure
from in-repo precedent in the commit message — that is where a reviewer looks, and it does
not go stale the way an inline defense does.

**Register each new file with the build as you create it, not later.** A source file the
build system does not include is not built: its code is dead, its tests never run, and every
gate passes. That is the single most expensive mistake available, because nothing reports it.
`{{build_manifest}}` is where this project records it.

Catch cross-cutting impact in the same pass rather than waiting for runtime to surface it.
Any time you rename a symbol, change a signature, add a user-facing string, or add a setting
— grep for every dependent and update it now. The silent-failure list for this project is in
`{{mechanics_gate_dod}}`; each entry fails quietly rather than loudly.

When a grep reveals a class of problem rather than a single instance, fix every instance in
that pass. "Only this one is failing" is not the same as "only this one is a bug." Excluding
an instance, deferring anything, or creating any work item all go through `deliver`'s
benign-in-context bar and deferral procedure.

### 2b. Read the diff before staging

Run the "Before `git add`" checks in `${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` —
extract duplicated logic, cut comments that restate the code or narrate history, confirm no
ticket ID reached a source comment. Then stage.

### 2c. Adversarial review, before the commit

Launch the `commit-adversary` subagent.

**The delegation prompt contains only:** the git range (`git diff` against the previous
commit, or `--cached` for staged work), the covering ticket IDs, and nothing else. Do not
describe what you changed. Do not explain why. Do not tell it what to look for or where you
think the risk is. It reads the diff cold and derives its own context.

Fix every BLOCKER and MAJOR. Address PATTERN SPREAD findings in this same commit unless they
are genuinely out of scope, in which case say so explicitly and note them for the branch
review. Re-run the review on the fixed diff. Repeat to a maximum of three rounds; if BLOCKERs
persist after the third, stop and bring it to Rob, declaring the stop per `deliver`'s
invariants.

Before round 3, apply `deliver`'s revert rule: if round 2's findings were mostly against what
round 1's fix introduced rather than against the phase's own code, revert that fix and take a
different approach instead of running a third round. Do not build a guard to satisfy a
finding here — `deliver`'s enforcement-machinery invariant makes that a separate ticket.

### 2d. Definition of Done, then commit

Run every gate in `${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` and
`{{mechanics_gate_dod}}`, including the conditional ones that apply to this phase's diff.
All green. Read the result file at `{{results_file}}`, never exit codes.

Commit with the ticket ID in the message, then mark this phase `"done": true` and fill in
`finished_at`, `commit`, and `files` from the commit just made. If the file is missing — a
resumed session, or this skill re-entered on an existing branch — rebuild it from the plan
document's phase list, marking `done: true` every phase whose commit is already on the
branch, and backfill from `git log`. Leave a rebuilt phase's timestamps absent rather than
inventing them; report its duration as `unknown`.

Then update `acceptance_criteria`: set `met: true` on every AC this phase satisfied, and put
in `evidence` the specific thing that demonstrates it — a test name, a file and symbol, a
gate that now passes. An AC is met when something checkable shows it, not when the code that
ought to satisfy it exists. If nothing checkable exists yet, the AC stays `false` and its
evidence is what is still missing.

**An AC whose `verified_by` names an out-of-band tier stays `false` until that verification
runs**, no matter how complete the code looks. Its evidence field says what is still
outstanding. A green automated suite is not evidence for it — the suite is silent on exactly
that behavior, per `{{failure_policy_gate}}`.

### 2e. Phase status report

Report before starting the next phase, then move directly to the next one without pausing
for a reply. The format — heading, phase table, files, acceptance criteria, gates — is
`${CLAUDE_PLUGIN_ROOT}/gates/status-report.md`. Read it once per session. Friction is
recorded to `friction[]` there, never printed in a phase report.

## Step 3 — Report

When all phases are committed, report:

1. **The cumulative phase table** — all phases `done`, with per-phase durations and the run
   total.
2. **The commit list** — one line each, SHA and subject.
3. **All files modified across the branch**, from
   `git diff --stat {{parent_branch_default}}...HEAD`. This is the last point before
   `/branch-review` where an unintended file is cheap to catch.
4. **Final acceptance criteria table** — every AC with its evidence, and every AC awaiting
   out-of-band verification listed separately as outstanding work. This is the handoff
   artifact: `/ship-pr` builds the PR body from it, and any AC still unmet must be stated as
   such before the branch review rather than discovered in it. All ACs met is a claim about
   the ticket being deliverable — make it explicitly, or say which are not and why.
5. **Friction recorded** — the count in `friction[]`, one line, and nothing more. Do not
   list the items, do not propose wording, do not stop to ask. The whole list reports once
   at the end of delivery, from `/ci-green`, where it can dedupe across every stage. Halting
   implementation for a config conversation before the branch has even been reviewed is what
   that change removed.

Do not push. Do not open a PR. `/ship-pr` covers that, after `/branch-review`.

## Standing rules

- Never dismiss a failing test as a known flake. Policy: `{{failure_policy_gate}}`.
- If Rob says something is broken, investigate before responding. Never lead with
  reassurance — his view of the running application is authoritative, and tool output can be
  stale or silent on exactly what he is looking at.
- Update the user-facing docs named in `{{user_docs_targets}}` as part of the phase that
  changes behavior, not afterward.
