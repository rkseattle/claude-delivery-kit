---
name: deliver
description: End-to-end delivery of one or more Jira work items — plan, adversarial design review, approval gate, phased implementation with per-commit adversarial review, cold branch review, PR, and CI to green.
argument-hint: <TICKET-N> [TICKET-N ...]
disable-model-invocation: true
---

Deliver: $ARGUMENTS

You are the orchestrator. Each stage is a skill in this plugin. They carry
`disable-model-invocation: true` because they create branches, transition Jira, push, and
open PRs — they must not fire on their own. So **do not call them with the Skill tool; it
will be blocked.**

Instead, at the moment you reach each stage, **read that stage's `SKILL.md` with the Read
tool and follow it in full as written.** Read it when you get there, not up front — that
keeps each stage's instructions out of context until they are needed. They live beside
this file at `${CLAUDE_PLUGIN_ROOT}/skills/<stage>/SKILL.md`.

Ignore the `argument-hint`, `allowed-tools`, and `disable-model-invocation` fields in
those files when read this way; they apply only to direct slash-command invocation. The
body is the procedure.

**Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` now.** It names this project's ticket
prefix, commands, result files, and gate mechanics. Every double-braced placeholder below
and in the stage files resolves from it. If it is absent, say so and stop: the workflow
cannot run without knowing what to run.

## Step 0 — Resume or start fresh

**Before stage 1, before anything else**, read `.claude/state/current-plan.json`.

| State                                            | Action                                            |
| ------------------------------------------------ | ------------------------------------------------- |
| Absent, or its `branch` is not checked out       | Fresh run — go to stage 1                         |
| Present, unfinished, tickets match or none given | **Resume path** below                             |
| Present, but $ARGUMENTS names different tickets  | **Stop and ask.** Never start over the top of it. |

A session resuming mid-run has read none of this workflow's machinery: stage files are
read on arrival and gates when they apply, so a run entered in the middle skips every one
of those reads. The state file records _where_ the work is and cannot carry the
instructions — a gate copied into JSON is a copy free to drift — so a resume re-reads the
real files in the order a run would have reached them.

**The resume path's first action — before touching code, git, or a subagent:**

1. This file's **Invariants** section below. It is already in context; do not skip it.
2. The `SKILL.md` of the stage named in `stage`.
3. That stage's gates: `definition-of-done.md` for stage 2 · `pre-push.md` for stage 4 ·
   `status-report.md` for any stage that reports · plus every gate named in
   `project.json`'s `extra_gates`.
4. The plan document at `plan`.

Then **report what you loaded and where you landed** — the file list, the stage and step,
the phases done and remaining — and continue without waiting for a reply. The report is
the verification: a resume that silently loaded nothing is visible because its list is
missing or wrong. Skipping the report is how this failure recurs unnoticed.

**An uncommitted phase never started.** A dirty tree never passed the Definition of Done,
so it gets no credit for having been done: re-enter that phase at its first step, keep
the existing edits as a starting point, and say so in the report. Trusting a partial diff
ships code that skipped the gate it was interrupted before reaching.

The marker may be stale by one step, since a crash lands between writes. `git status`,
`git log`, and the phase list win wherever they disagree with it.

## Stages

1. **`plan-work`** — substitute $ARGUMENTS for the ticket IDs. Tickets, codebase survey,
   phased plan, adversarial design review, then present for approval.
   → **Hard stop.** Wait for explicit approval. A clarifying question is not approval.

2. **`implement-phases`** — substitute the path of the plan file written in stage 1.
   Branch, Jira to In Progress, then every phase implemented, adversarially reviewed, and
   committed, straight through with no pause between phases.

3. **`branch-review`** — base ref `{{parent_branch_default}}`. Cold Greptile-style review
   of the whole branch in an isolated subagent; fix by root cause and propagate each fix
   pattern across the codebase.

4. **`ship-pr`** — substitute $ARGUMENTS for the ticket IDs. Pre-push gate, clean tree,
   push, PR, Jira to In Review.

5. **`ci-green`** — the PR opened in stage 4. Monitor CI and PR feedback; root-cause every
   failure in an isolated subagent; loop until fully green with no unaddressed comments.
   Then, and only then, delete the run's scratch files — the state file and the plan — so
   Step 0 cannot resume a run that already shipped.

Stages 2 through 5 run without further approval gates. Surface real decisions as they
arise; do not ask permission to continue.

Rob can also run any stage on its own as a slash command. If he has already run one
manually in this session, pick up from the next rather than repeating it.

## Invariants across every stage

**Adversarial reviews stay blind.** Every delegation to `design-adversary`,
`commit-adversary`, `greptile-reviewer`, or `ci-failure-adversary` carries only refs — a
file path, a git range, a branch name, ticket IDs, failure evidence. Never your reasoning,
never a summary of what you changed, never a hint about where the risk is. Their entire
value is having no implementation context; anything you add spends it. Cap every review
loop at three rounds, then escalate the disagreement to Rob.

**A round that finds defects in the previous round's fix means revert, not iterate.** The
three-round cap counts rounds; it does not notice what they are about. Before starting any
round after the first, ask what the last round's findings were against: the code the branch
set out to change, or the code the previous round wrote to satisfy a finding. When it is
predominantly the latter, stop. Revert that fix and take a different approach — or bring
the disagreement to Rob if no other approach is apparent.

Two consecutive rounds finding defects in each other's output is not convergence, and a
third round will not reach it. It means the fix is the wrong shape: the reviewer is
exploring a design that should not exist rather than a defect that should be gone. Each
further round adds surface for the next one to find, which is why these loops end at the
cap rather than at APPROVE.

**Industry-standard patterns only.** Never the simplest, quickest, or easiest solution.
Follow in-repo precedent where it exists; justify every departure in writing.

**Root cause, then pattern spread.** Every fix — plan finding, review finding, test
failure, CI failure, PR comment — gets root-caused, and the codebase gets grepped for
other instances of that same cause. Fix all live instances in the same pass.

**Enforcement machinery is never built inside a feature branch.** Fixing an instance is
this branch's job; building the guard that would catch the next one is not. If a finding
argues for new machinery — a hook, a check script, a CI job or filter, a lint rule, a
self-test harness — fix the instance and every live instance of its root cause, then
propose the guard to Rob as its own ticket. Do not build it here.

The reason is measured, not theoretical. A guard written under review pressure is written
without a plan and without a design review, and then the review rounds turn on the guard:
one branch shipped its feature in a single commit and spent seven more rewriting a branch
guard four times, each round closing a bypass the previous round opened. A Stop hook
reached 503 lines across nine rounds the same way. Both were built mid-branch to prevent
something cheaper than what they cost.

This binds regardless of how small the guard looks or how confident the finding is. "It's
twenty lines" is how both of those started. A guard is a program with its own failure
modes, and its only failure mode is silence — which is exactly what a rushed one produces.

**And a guard usually drags CI config with it.** A workflow edit can widen test selection
to everything, and single-purpose filter outputs accumulate. When a guard does earn its own
ticket, the plan must reach an existing filter rather than adding one — the ordered list is
in the project's Definition of Done mechanics.

**Fixing is the default; deferring is the exception that needs permission.** An instance of
a root cause this work already fixes is excluded only when it is **benign in its context** —
it cannot produce a wrong result for any user or any test. "It's a different feature", "it's
a different view", "it's a different workspace", "it's a big diff", "it deserves its own
review surface" are _not_ benign — they describe every pattern-spread fix ever made. Neither
is "the automated suite cannot reach it". State the exclusion in benign terms or fix it.

**Never create a Jira work item without asking first.** Filing a ticket feels like handling
the problem and is not; a ticket you file when you could have fixed the thing is deferral
with extra steps. Before creating any issue, follow this order:

1. **Test the deferral adversarially.** Launch `commit-adversary` with only: the file and
   line, the root cause, and your one-sentence benign claim. No branch context, no
   rationale, no mention that you would rather not do the work. If it disagrees, fix the
   instance and do not file anything.
2. **If it agrees, ask Rob** — the finding, why it is benign, the cost of fixing it now
   versus later, and your recommendation. Wait for an explicit answer.
3. **Only then create the ticket**, with Acceptance Criteria per `CLAUDE.md`.

This applies to every stage and to tickets of any kind — follow-ups, spin-offs, "while we
were in there" observations. Recording a finding in the PR body or in chat needs no
permission; creating a work item does.

**Deleting or closing someone else's work item needs permission too**, and for the opposite
reason: it is not reversible from here, and a ticket you delete is a decision someone else
can no longer see. Ask, and say what happens to the work it tracked. Moving a ticket through
its normal workflow states — In Progress, In Review — is a routine step and needs no
permission.

**No failure is ever a known flake.** Full policy, including what does not count as a
failure at all: the failure-handling section of `{{failure_policy_gate}}`.

**Gates are unconditional.** Definition of Done before every commit
(`${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` plus `{{mechanics_gate_dod}}`).
Pre-push checklist before every push (`${CLAUDE_PLUGIN_ROOT}/gates/pre-push.md` plus
`{{mechanics_gate_pre_push}}`). Read result files, never exit codes or console output.

**Jira transitions are real steps.** In Progress before the first line of code, In Review
after the PR opens. Look up the issue's available transitions via the Atlassian MCP first —
never guess a transition ID.

**Report full status at every phase and stage boundary.** Finishing a phase or a stage is
never just a line saying it is done. `${CLAUDE_PLUGIN_ROOT}/gates/status-report.md` defines
the format; stages 3 through 5 report the same things scaled to what they do — a stage that
fixes review findings still says which files it touched, how long it ran, and which ACs it
moved. A boundary crossed without a status report is the single most common way a run
becomes unreviewable: the information exists only while the phase is fresh, and
reconstructing it afterward from `git log` loses the timing and the friction entirely.

**Process feedback is recorded as it happens and reported once, at the end.** Every stage
appends friction to `friction[]` in `.claude/state/current-plan.json` and prints nothing;
`ci-green` reports the whole list before it deletes that file. One list at the end dedupes
across every stage, which four separate per-stage reports could never do, and it stops a
config conversation interrupting a run mid-flight.

**It is proposed, never applied on your own initiative.** The reasoning is the same as for
work items: a config file that grows unprompted stops being read, and these files only work
because everything in them earned its place. `none` is a valid and common finding.

**These files have a line budget.** Every run is asked for friction and no run is asked what
to remove, so the corpus ratchets in one direction unless something holds it. Each file has
a cap:

| File                              | Cap |
| --------------------------------- | --- |
| `CLAUDE.md`                       | 400 |
| Any gate (`status-report.md`: 130) | 300 |
| Any skill `SKILL.md`              | 320 |
| Any agent definition              | 130 |

A project may tighten a cap in `project.json`; it may not raise one without Rob.

The caps sit just above today's sizes deliberately: the next addition to a near-full file
has to displace something. **A proposal that would breach a cap must name what comes out** —
the rule it replaces, narrows, or makes redundant — and that removal is part of the same
proposal, not a follow-up. If nothing can come out, the proposal is that the rule matters
more than what is already there; say so and let Rob weigh them against each other.

Prefer replacing to appending in every case, cap or no cap. A new rule covering the same
ground as an existing one produces two rules that drift, and the drift is invisible until a
run follows the stale one. Raising a cap is a decision for Rob, and it is the answer only
when the file genuinely covers more ground than it used to.

**Shared before project.** A rule that would hold in any project belongs in this plugin, not
in a project file. A copy made project-side is a copy free to drift, and the drift is
invisible until two projects disagree. Propose it here and name the project copies it
replaces.

**Stay quiet while monitors run.** No filler turns, no polling loops, no narrating the wait.

**Reversibility decides whether to ask, not phrasing.** A message ending in a question mark
is not automatically a discussion, and one phrased as an instruction is not automatically
licence for an irreversible act. Ask what the work would actually do:

- **Cheap to undo — act, and say what you did.** A local edit, a new file, a scratch
  script, an uncommitted experiment. `git checkout` reverses all of it in seconds, so
  answering the question _and_ doing the work costs one round trip instead of two. A
  question about the repo usually wants the answer demonstrated, not described.
- **Costly or impossible to undo — stop and ask.** A push, a force-push, a PR, a Jira
  write, a deleted branch, a destructive DB command, anything reaching a system outside
  this checkout. These stop even when the message reads as an instruction, because the
  cost of being wrong is not symmetrical with the cost of asking.

The middle case — a commit — follows the work: commit freely on a feature branch, ask
before committing to `{{parent_branch_default}}`.

**Authorization already given is not asked for twice.** This rule governs an external write
nobody has approved yet — the ad-hoc request, the "while you're in there". It does not
re-gate the stages of an approved run: stage 1's approval covers the push, the PR, and the
Jira transitions that stages 2 through 5 exist to perform, which is what "stages 2 through 5
run without further approval gates" above means. Stopping at `ship-pr` to ask permission to
push would deadlock the workflow at its final stage.

The test is whether _this specific operation_ was authorized, not whether it is
irreversible. An approved plan authorizes its own delivery; it does not authorize an
unrelated force-push, a ticket nobody asked for, or a bypass of a gate that just failed.

**Prefer a stated assumption to a blocking question.** When a choice has an obvious default
and the resulting work is cheap to redo, take the default, say in one line which assumption
you made, and keep going. A correction then costs an amend rather than a round trip. Reserve
a blocking question — ending the turn with nothing delivered — for when proceeding wrongly
would be unsafe, would be expensive to unwind, or would waste substantial work if the guess
is wrong.

Do everything that does not depend on the answer first. A question that blocks one phase
rarely blocks all of them, and arriving with four phases done and one question is a far
better turn than arriving with the question alone.

**Batch open decisions into one turn.** When several genuinely need Rob, ask them together —
one `AskUserQuestion` with every open choice, each carrying a recommendation and its
consequence — rather than serializing them across turns. Two questions asked separately cost
two round trips and make a run look stalled twice.

**Keep the stage marker current as you go.** Every stage writes `stage` and `stage_step` into
`.claude/state/current-plan.json` when it starts and at each of its own step boundaries,
naming the step as that stage's file names it (`"2c — adversarial review, phase 3"`). Write
it _before_ the step, not after: the value of the marker is that a session killed without
warning — a reboot, a lost terminal — left the last write behind, and a marker written on the
way out is exactly the one a crash never writes.

This is what Step 0 reads. A stage that skips these writes leaves the next session inferring
its position from git alone, which cannot distinguish a branch awaiting review from one
awaiting CI.

**Declare a deliberate stop.** Any stage may end a turn to ask Rob something — a genuine
decision, a deferral, persistent BLOCKERs, an ambiguous test scope. Whenever that happens
with phases still unfinished, set `"paused": true` in `.claude/state/current-plan.json`
first, and clear it as the first action of the turn that resumes. The `Stop` hook cannot tell
a question from a stall, by design: distinguishing them would mean classifying prose.
Declaring the stop is what separates them. The branch guard reads the same field.

That hook only guards stops _inside_ a plan, and most turns are not inside one. So it is a
backstop for a control that has to be behavioral: nothing catches a false pause taken outside
a plan except not taking it. A sentence naming the next action is never the last thing in a
turn — either its tool call goes in the same message, or the sentence is not written.

## If a stage file is missing or unreadable

Stop and say which one. Do not reconstruct the procedure from memory — the gates and review
protocols are the point of the workflow.
