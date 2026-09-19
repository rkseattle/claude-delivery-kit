# Ticket rubric — what `plan-work` needs from a ticket

`write-tickets` writes against this file and `ticket-adversary` reviews against it. Each
criterion names the `plan-work` behavior it prevents. `plan-work` is where a loose ticket
becomes a split proposal, a `Deviation`, or an AC clause with no phase — so a ticket is
ready when `plan-work` can plan it without doing any of the three.

Limits are not restated here. The handoff limit is in `plan-work` Step 1 and the phase
limit is in its **Size** section; read them from
`${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md` so there is one number to change.

## Story, Task, Bug

**R1 One outcome.** Summary and Behavior/Change describe one behavior change; every AC
verifies part of it. A refactor bundled with a feature is its own Task, linked Blocked by.
Prevents: split proposal.

**R2 Plannable within the limits.** A phase sketch in `plan-work`'s shape — each phase
builds on its own under `{{build_command}}` — fits the phase limit. Tickets sharing a
`Handoff:` label fit the handoff limit. Prevents: split proposal at Step 1 or at Size.

**R3 Grounded.** Every `(modify)`/`(delete)` touch point exists, or a Blocked-by ticket
creates it. Every function, type, route, table, config key, or UI element the ticket
names exists and behaves as stated — checked in the code, not inferred from file names.
Prevents: design-adversary BLOCKER on a false "X currently does Y", then a re-plan.

**R4 Registry consumers listed.** For every symbol the ticket edits that
`{{registry_file}}` names, or that other files enumerate, switch over, render, or assert
against, `grep -rln "<SYMBOL>" {{source_roots}}` was run and every consumer that changes
is a touch point. Prevents: the phase count growing at plan time until it breaches Size.

**R5 Pattern spread settled.** For a bug or any fix of a root cause, the other live
instances were grepped for. Each is either covered by an AC or listed in Out of scope as
**benign in context** — the bar in `${CLAUDE_PLUGIN_ROOT}/skills/deliver/references/invariants.md`.
Prevents: sequenced-ticket proposal, or a design-adversary finding on the exclusion.

**R6 Decided.** No TBD, alternatives ("X or Y"), or instruction to investigate, explore,
consider, or decide. Where a choice changes the result — data format, error shape, UI
copy, limit, library, owning layer — the ticket states it. A choice that needs research
is a spike Task whose AC is a committed decision record; dependents are Blocked by it.
Prevents: an open question at the approval gate.

**R7 Verifiable per clause.** `plan-work` splits every AC on commas and semicolons into
one row per clause. Each clause is observable with concrete values — status codes, error
bodies, field names, counts, UI text — and each AC ends `[verify: <tier> @ <evidence>]`
with `<tier>` from `{{verification_tiers}}`. For an automated tier, evidence is a test
path whose file or directory exists and holds tests of that tier. A clause only an
out-of-band tier can settle says so, so it surfaces at approval, not at ship.
Prevents: an unphased clause, or a `Verified by` cell the plan cannot fill.

**R8 Dependencies stated in the ticket.** Code the ticket relies on exists on
`{{parent_branch_default}}` or comes from a Blocked-by ticket. Every dependency is in the
Dependencies section in prose, with status — `plan-work` reads descriptions for sequencing,
not link metadata alone. Prevents: a phase that does not build.

**R9 Bounded.** Out of scope names the adjacent work a planner would plausibly include and
where it lives (another ticket, or "not planned"). Prevents: scope growth, then a split.

**R10 Self-contained.** Readable cold from the ticket, its epic, its blockers, `CLAUDE.md`,
and the repo. No "as discussed", no undefined abbreviations, no content that lives only
behind a link. Prevents: a misread plan.

**R11 Consistent.** No AC contradicts another AC, a sibling ticket, or existing tested
behavior, unless the ticket states the change to that behavior. No two tickets change the
same behavior. Prevents: a `Deviation` row.

## Bug, in addition

**B1 Reproducible.** Steps use specific inputs; Environment names the commit or build;
Expected and Actual are separate.

**B2 Regression clause.** One AC, marked `Regression:`, is an automated test that fails on
the current code and passes after the fix.

**B3 Root cause.** Stated with `file:line`, or the touch points name the suspected area and
B2 holds. Otherwise a diagnosis Task comes first — AC: a committed failing test and a
root-cause note — and the Bug is Blocked by it.

## Epic

**E1** Goal is an outcome; each success measure is observable.
**E2** Every success measure lists at least one child, and those children's ACs together
demonstrate it.
**E3** Every child maps to a success measure or carries the `enabling` label.
**E4** Blocked-by links form no cycle; Children is in build order.
**E5** Out of scope is present and non-empty.

## Severity

`ticket-adversary` uses the kit's scale:

- **BLOCKER** — `plan-work` would propose a split, write a `Deviation`, or leave a clause
  unphased; or a claim about the code is false (R1–R5, R7, R11, B2).
- **MAJOR** — another criterion fails.
- **MINOR** — clarity only.
- **DECISION** — only Rob can resolve it. Stated as a question.
