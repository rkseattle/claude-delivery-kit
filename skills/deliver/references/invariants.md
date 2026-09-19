# Invariants — the reasoning behind each rule

`deliver`'s SKILL.md states each invariant in one line. This file holds the reasoning,
the measured incidents, and the bounds — read it when a stage must actually adjudicate
one, not on every run.

## Contents

- Adversarial reviews stay blind
- Revert, not iterate
- Industry-standard patterns only, and the standard is named
- Root cause, then pattern spread
- Enforcement machinery is never built inside a feature branch
- Fixing is the default; deferring needs permission
- Never create a Jira work item without asking
- Report full status at every boundary
- Friction and citations: recorded as they happen, reported once
- The line budget
- Shared before project
- Reversibility decides whether to ask
- Prefer a stated assumption to a blocking question
- Declare a deliberate stop

## Adversarial reviews stay blind

Every delegation to `design-adversary`, `commit-adversary`, `greptile-reviewer`,
`ci-failure-adversary`, or `ticket-adversary` carries only refs — a file path, a git
range, a branch name, ticket IDs, failure evidence. Never your reasoning, never a summary
of what you changed, never a hint about where the risk is.

Their entire value is having no implementation context; anything you add spends it. Cap
every review loop at three rounds, then escalate the disagreement to Rob.

## Revert, not iterate

The three-round cap counts rounds; it does not notice what they are about. Before
starting any round after the first, ask what the last round's findings were against: the
code the branch set out to change, or the code the previous round wrote to satisfy a
finding. When it is predominantly the latter, stop. Revert that fix and take a different
approach — or bring the disagreement to Rob if no other approach is apparent.

Two consecutive rounds finding defects in each other's output is not convergence, and a
third round will not reach it. It means the fix is the wrong shape: the reviewer is
exploring a design that should not exist rather than a defect that should be gone. Each
further round adds surface for the next one to find, which is why these loops end at the
cap rather than at APPROVE.

## Industry-standard patterns only, and the standard is named

This includes the replacement approach after a revert. Never the simplest or easiest
solution. "A different approach" drawn from the same reading of the surrounding code
produces the same shape and fails the same way; that is the loop.

Name the documented standard, framework convention, or known implementation the approach
is an instance of, before writing it. In-repo precedent justifies a choice only where you
can name it that way too — one you cannot is local invention, and following it spreads
it. If nothing external fits, that is the finding to bring to Rob.

Every stage appends what it cited to `citations[]` and prints nothing; `ci-green` reports
the whole list once, before it deletes that file. Justify every departure in writing.

## Root cause, then pattern spread

Every fix — plan finding, review finding, test failure, CI failure, PR comment — gets
root-caused, and the codebase gets grepped for other instances of that same cause. Fix
all live instances in the same pass.

## Enforcement machinery is never built inside a feature branch

Fixing an instance is this branch's job; building the guard that would catch the next one
is not. If a finding argues for new machinery — a hook, a check script, a CI job or
filter, a lint rule, a self-test harness — fix the instance and every live instance of its
root cause, then propose the guard to Rob as its own ticket. Do not build it here.

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
to everything, and single-purpose filter outputs accumulate. When a guard does earn its
own ticket, the plan must reach an existing filter rather than adding one — the ordered
list is in the project's Definition of Done mechanics.

## Fixing is the default; deferring needs permission

An instance of a root cause this work already fixes is excluded only when it is **benign
in its context** — it cannot produce a wrong result for any user or any test.

"It's a different feature", "it's a different view", "it's a different workspace", "it's a
big diff", "it deserves its own review surface" are _not_ benign — they describe every
pattern-spread fix ever made. Neither is "the automated suite cannot reach it". State the
exclusion in benign terms or fix it.

## Never create a Jira work item without asking

Filing a ticket feels like handling the problem and is not; a ticket you file when you
could have fixed the thing is deferral with extra steps. Before creating any issue:

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

**Deleting or closing someone else's work item needs permission too**, and for the
opposite reason: it is not reversible from here, and a ticket you delete is a decision
someone else can no longer see. Ask, and say what happens to the work it tracked. Moving a
ticket through its normal workflow states — In Progress, In Review — is routine and needs
no permission.

## Report full status at every boundary

Finishing a phase or a stage is never just a line saying it is done.
`${CLAUDE_PLUGIN_ROOT}/gates/status-report.md` defines the format; stages 3 through 5
report the same things scaled to what they do — a stage that fixes review findings still
says which files it touched, how long it ran, and which ACs it moved.

A boundary crossed without a status report is the single most common way a run becomes
unreviewable: the information exists only while the phase is fresh, and reconstructing it
afterward from `git log` loses the timing and the friction entirely.

## Friction and citations: recorded as they happen, reported once

Every stage appends friction to `friction[]` and citations to `citations[]` in
`.claude/state/current-plan.json`, and prints nothing; `ci-green` reports both lists
before it deletes that file.

One list at the end dedupes across every stage, which four separate per-stage reports
could never do, and it stops a config conversation interrupting a run mid-flight.

**Both are proposed, never applied on your own initiative.** The reasoning is the same as
for work items: a config file that grows unprompted stops being read, and these files only
work because everything in them earned its place. `none` is a valid and common finding.

## The line budget

Every run is asked for friction and no run is asked what to remove, so the corpus ratchets
in one direction unless something holds it. Each file has a cap:

| File                               | Cap |
| ---------------------------------- | --- |
| `CLAUDE.md`                        | 400 |
| Any gate (`status-report.md`: 140) | 300 |
| Any skill `SKILL.md` + references  | 480 |
| Any agent definition               | 140 |

**A skill's cap covers its `references/` files too**, counted together with the body. The
split exists to cut what loads on every invocation, not to create room the budget cannot
see: a reference file is still text someone maintains, and an uncounted one is how the
ratchet resumes under a different name.

The skill cap is 480 rather than 320 because splitting a skill into references reflows
dense prose into more lines than it replaced — `deliver` went from 321 lines to 208 of
body plus 252 of reference. The per-invocation load fell 44%, which is what the budget
exists to control, while the raw total rose. A cap that punished that split would be
measuring the wrong quantity. The agent and gate caps moved 130 → 140 for the citations
work, which named no displacement when it landed.

A project may tighten a cap in `project.json`; it may not raise one without Rob.

The caps sit just above today's sizes deliberately: the next addition to a near-full file
has to displace something. **A proposal that would breach a cap must name what comes out**
— the rule it replaces, narrows, or makes redundant — and that removal is part of the same
proposal, not a follow-up. If nothing can come out, the proposal is that the rule matters
more than what is already there; say so and let Rob weigh them against each other.

Prefer replacing to appending in every case, cap or no cap. A new rule covering the same
ground as an existing one produces two rules that drift, and the drift is invisible until
a run follows the stale one. Raising a cap is a decision for Rob, and it is the answer
only when the file genuinely covers more ground than it used to.

## Shared before project

A rule that would hold in any project belongs in this plugin, not in a project file. A
copy made project-side is a copy free to drift, and the drift is invisible until two
projects disagree. Propose it here and name the project copies it replaces.

## Reversibility decides whether to ask

A message ending in a question mark is not automatically a discussion, and one phrased as
an instruction is not automatically licence for an irreversible act. Ask what the work
would actually do:

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

**Authorization already given is not asked for twice.** This rule governs an external
write nobody has approved yet — the ad-hoc request, the "while you're in there". It does
not re-gate the stages of an approved run: stage 1's approval covers the push, the PR, and
the Jira transitions that stages 2 through 5 exist to perform. Stopping at `ship-pr` to
ask permission to push would deadlock the workflow at its final stage.

The test is whether _this specific operation_ was authorized, not whether it is
irreversible. An approved plan authorizes its own delivery; it does not authorize an
unrelated force-push, a ticket nobody asked for, or a bypass of a gate that just failed.

## Prefer a stated assumption to a blocking question

When a choice has an obvious default and the resulting work is cheap to redo, take the
default, say in one line which assumption you made, and keep going. A correction then
costs an amend rather than a round trip. Reserve a blocking question — ending the turn
with nothing delivered — for when proceeding wrongly would be unsafe, would be expensive
to unwind, or would waste substantial work if the guess is wrong.

Do everything that does not depend on the answer first. A question that blocks one phase
rarely blocks all of them, and arriving with four phases done and one question is a far
better turn than arriving with the question alone.

**Batch open decisions into one turn.** When several genuinely need Rob, ask them together
— one `AskUserQuestion` with every open choice, each carrying a recommendation and its
consequence — rather than serializing them across turns. Two questions asked separately
cost two round trips and make a run look stalled twice.

## Declare a deliberate stop

Any stage may end a turn to ask Rob something — a genuine decision, a deferral, persistent
BLOCKERs, an ambiguous test scope. Whenever that happens with phases still unfinished, set
`"paused": true` in `.claude/state/current-plan.json` first, and clear it as the first
action of the turn that resumes.

The `Stop` hook cannot tell a question from a stall, by design: distinguishing them would
mean classifying prose. Declaring the stop is what separates them. The branch guard reads
the same field.

That hook only guards stops _inside_ a plan, and most turns are not inside one. So it is a
backstop for a control that has to be behavioral: nothing catches a false pause taken
outside a plan except not taking it. A sentence naming the next action is never the last
thing in a turn — either its tool call goes in the same message, or the sentence is not
written.

**When Rob asks to leave the branch, pause first — do not report a wall.** An explicit
instruction to switch branches, check out main, or step away from the work outranks the
guard: set `"paused": true`, then switch, then say the plan was paused and how to resume
it. Clear the field as the first action of the turn that comes back. The guard exists to
catch a stray checkout nobody asked for; answering a direct request with "a hook prevents
this" makes it look like the tooling is in charge, and the escape hatch it names in that
message is this one.
