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

Instead, on reaching each stage, **read its `SKILL.md` with the Read tool and follow it in
full as written** — on arrival, not up front, so each stage's instructions stay out of
context until needed. They live at `${CLAUDE_PLUGIN_ROOT}/skills/<stage>/SKILL.md`.

Ignore the `argument-hint`, `allowed-tools` and `disable-model-invocation` fields in those
files when read this way: they apply only to direct invocation. The body is the procedure.

**Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` now.** It names this project's ticket
prefix, commands, result files, and gate mechanics. Every double-braced placeholder below
and in the stage files resolves from it. If it is absent, say so and stop: the workflow
cannot run without knowing what to run.

**Confirm the kit is current before stage 1.** `/reload-plugins` reloads the cached version
only; a newer release needs `/plugin marketplace update` first. Report the version in use.

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

Rob may run any stage as a slash command; if he ran one this session, start at the next.

## Invariants across every stage

Each rule below is binding as stated. The reasoning, the measured incidents behind it,
and its bounds are in `${CLAUDE_PLUGIN_ROOT}/skills/deliver/references/invariants.md` —
read that file when a stage must actually adjudicate one, not on every run.

**Adversarial reviews stay blind.** Every delegation to `design-adversary`,
`commit-adversary`, `greptile-reviewer`, `ci-failure-adversary`, or `ticket-adversary`
carries only refs — a file path, a git range, a branch name, ticket IDs, failure evidence.
Never your reasoning, never a summary, never a hint about where the risk is. Cap every
review loop at three rounds, then escalate to Rob.

**A round that finds defects in the previous round's fix means revert, not iterate.** Ask
what each round's findings were against: the branch's own code, or the previous round's
fix. Predominantly the latter means the fix is the wrong shape — revert it and take a
different approach rather than running a third round.

**Industry-standard patterns only, and the standard is named** — including the replacement
approach after a revert. Name the documented standard, framework convention, or known
implementation the approach is an instance of, before writing it. In-repo precedent
justifies a choice only where you can name it that way too. If nothing external fits, that
is the finding to bring to Rob. Every stage appends what it cited to `citations[]`.

**Root cause, then pattern spread.** Every fix — plan finding, review finding, test
failure, CI failure, PR comment — gets root-caused, and the codebase gets grepped for
other instances of that same cause. Fix all live instances in the same pass.

**Enforcement machinery is planned before it is written.** A hook, check script, CI filter,
lint rule, or self-test harness may ship on a feature branch, but never from inside the
review round that asked for it: stop the loop, add a phase, write it there as its own commit.
Its AC is the invariant it enforces plus a self-test per known bypass, and a second bypass of
that invariant means revert and escalate, not a third round. This binds however small it
looks.

**Fixing is the default; deferring is the exception that needs permission.** An instance is
excluded only when it is **benign in its context** — it cannot produce a wrong result for
any user or any test. A different feature, view, workspace, or review surface is not
benign; neither is a large diff, nor "the automated suite cannot reach it".

**Never create a Jira work item without asking first**, and never delete or close someone
else's. The three-step deferral procedure — `commit-adversary` on the benign claim, then
Rob's explicit answer, then the ticket — is in the reference file. Moving a ticket through
its normal states is routine and needs no permission.

**No failure is ever a known flake.** Full policy, including what does not count as a
failure at all: the failure-handling section of `{{failure_policy_gate}}`.

**Gates are unconditional.** Definition of Done before every commit
(`${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` plus `{{mechanics_gate_dod}}`).
Pre-push checklist before every push (`${CLAUDE_PLUGIN_ROOT}/gates/pre-push.md` plus
`{{mechanics_gate_pre_push}}`). Read result files, never exit codes or console output.

**Jira transitions are real steps.** In Progress before the first line of code, In Review
after the PR opens. Look up the issue's available transitions via the Atlassian MCP first —
never guess a transition ID.

**Report full status at every phase and stage boundary.**
`${CLAUDE_PLUGIN_ROOT}/gates/status-report.md` defines the format; stages 3 through 5
report the same things scaled to what they do. A boundary crossed without a report is the
most common way a run becomes unreviewable.

**Friction and citations are recorded as they happen and reported once, at the end.** Every
stage appends to `friction[]` and `citations[]` and prints nothing; `ci-green` reports both
before it deletes that file. Both are proposed, never applied on your own initiative.

**These files have a line budget**, and a skill's cap covers its `references/` files
counted with the body:

| File                               | Cap |
| ---------------------------------- | --- |
| `CLAUDE.md`                        | 400 |
| Any gate (`status-report.md`: 140) | 300 |
| Any skill `SKILL.md` + references  | 480 |
| Any agent definition               | 140 |

**A proposal that would breach a cap must name what comes out.** Prefer replacing to
appending in every case. A project may tighten a cap in `project.json`; raising one is
Rob's decision alone.

**Shared before project.** A rule that would hold in any project belongs in this plugin,
not in a project file. Propose it here and name the project copies it replaces.

**Stay quiet while monitors run.** No filler turns, no polling loops, no narrating the wait.

**Reversibility decides whether to ask, not phrasing.** Cheap to undo — act, and say what
you did. Costly or impossible to undo — a push, a force-push, a PR, a Jira write, a deleted
branch, anything reaching outside this checkout — stop and ask, even when the message reads
as an instruction. Commits follow the work: freely on a feature branch, ask before
`{{parent_branch_default}}`.

**Authorization already given is not asked for twice.** Stage 1's approval covers the push,
the PR, and the Jira transitions stages 2 through 5 exist to perform. The test is whether
_this specific operation_ was authorized, not whether it is irreversible.

**Prefer a stated assumption to a blocking question**, and do everything that does not
depend on the answer first. When several decisions genuinely need Rob, **batch them into
one turn** rather than serializing them.

**Keep the stage marker current as you go.** Every stage writes `stage` and `stage_step`
into `.claude/state/current-plan.json` when it starts and at each of its own step
boundaries. Write it _before_ the step: a marker written on the way out is exactly the one
a crash never writes. This is what Step 0 reads.

**Declare a deliberate stop.** Ending a turn to ask Rob something with phases unfinished
means setting `"paused": true` first, and clearing it as the first action of the turn that
resumes. The `Stop` hook cannot tell a question from a stall by design; declaring the stop
is what separates them.

**When Rob asks to leave the branch, pause first — do not report a wall.** An explicit
instruction to switch branches outranks the guard: pause, switch, then say the plan was
paused and how to resume it.

## If a stage file is missing or unreadable

Stop and say which one. Do not reconstruct the procedure from memory — the gates and review
protocols are the point of the workflow.
