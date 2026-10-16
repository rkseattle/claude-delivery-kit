---
name: plan-work
description: Research Jira work items and the codebase, produce a phased implementation plan, have it adversarially reviewed, and present it for approval. Produces no code.
argument-hint: <TICKET-N ...> or <label>
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Bash, Task, WebSearch, WebFetch
---

Plan the work for: $ARGUMENTS

This skill produces a plan and stops. **No file in the repo is created, edited, or staged
during this skill**, other than the plan document itself. No branch, no Jira transition,
no commit. The approval gate at the end is real.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` first: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly.

## Step 1 — Resolve the arguments to a ticket set

$ARGUMENTS may be ticket IDs, a label, or a mix. Resolve before fetching.

**Matches `{{ticket_prefix}}-\d+`** → a ticket ID. Use directly.

**Anything else** → treat as a label and resolve it:

```
project = {{jira_project}} AND labels = "<label>" ORDER BY created ASC
```

**If that returns nothing, do not conclude the label is unused.** `~` is fuzzy text
matching against a text index, not glob — `labels ~ "foo-pr*"` will not match `foo-pr-03`.
An empty exact match almost always means the slug you were given is a prefix or fragment
of the real label. Recover by widening, not by giving up:

1. `project = {{jira_project}} AND labels ~ "<distinctive-fragment>"` — a single word from
   the middle of the slug works better than the leading token
2. If still empty, list broadly — `project = {{jira_project}} ORDER BY created DESC` — and
   read the actual label strings off recent issues
3. Re-run the exact `labels = "<full-slug>"` match once you have the real string

Report the resolved label if it differed from what you were given.

**Then, before going further:**

- Report the resolved ticket set — IDs and summaries — so the scope is visible.
- **If it resolves to more than 3 items, stop and flag it.** The working limit for a single
  handoff is 3; a larger group should be split before planning, not planned as one unit.
  Propose a split and wait.
- Order the set by its implied sequence. Where labels are numbered to match implementation
  order, that ordering is meaningful for phase sequencing.

## Step 2 — Fetch the tickets, sequentially

Fetch each resolved ticket and read the full description, acceptance criteria, and NFR
lines **before launching anything else**. Do not parallelize the fetch with exploration.
The session context contains recent git commits, and launching an exploration agent before
the ticket content is known anchors it on the wrong domain — this has happened.

Read linked and blocking tickets too, and the parent Epic's NFR lines. Cross-story
dependencies are often written in prose inside descriptions rather than as Jira links, so
read the descriptions for sequencing constraints rather than relying on link metadata.

## Step 3 — Survey the problem, then explore the codebase

**First, and before any `Explore` agent launches**, survey the whole problem the tickets
describe, per `deliver`'s invariant: name two or three real systems that solve it —
documented standards, framework conventions, well-known implementations — using WebSearch
and WebFetch in this context, scoped by the tickets alone. The ticket's own design is one
proposal to check against them, not the answer. Note the survey in chat before reading any
code, and carry it into `Approach` at Step 4: a survey done after or alongside the code
reads starts from what the code already does.

Then, and only then, explore the code. Delegate breadth to `Explore` subagents so it does
not consume the main context; run several in parallel across distinct questions. Give each
one ticket-derived scope, not commit-derived scope.

Establish:

- Where the affected domain currently lives — which directories and which specific files
- The in-repo pattern for the thing being built, if any: a proposal weighed against that
  survey, never followed by default.
- Blast radius: every caller, import, config key, script, and build-manifest reference
- Existing test coverage and where new coverage lands
- The decisions in `CLAUDE.md` and the project's reference docs that bear on it

### Enumerate every registry consumer with a command, not from memory

A **registry** is any single source of truth that other files enumerate, switch over,
render, or assert against. Editing one looks like a one-line change and is not: the line is
a fan-out point, and the real work is in its consumers.

For every registry the plan will touch, **run the grep and paste the file list into the
phase that edits it.** Not "consider the blast radius" — run it:

```bash
grep -rln "<SYMBOL>" {{source_roots}}
```

**This project's registries, and the consumer class each one hides, are in
`{{registry_file}}`.** Read it before planning any edit to a shared symbol. The table there
is not exhaustive: when a plan edits a symbol that other files enumerate, switch over, or
assert against, it is a registry — grep it and list what came back.

**A registry edit is never a one-line phase entry.** State, per consumer, what changes
there. If the answer is "nothing", say why — the alternative is discovering it in review.

Read the actual code. Do not plan from file names.

## Step 4 — Write the plan

Write it to `docs/plans/<primary-ticket>.md`. This is the one file this skill creates, and
it is gitignored working state, not a source file.

Structure:

```markdown
# <TICKET-N ...> — <title>

## Scope

What ships. What explicitly does not.
Covering tickets, and the label if the work was resolved from one.

## Acceptance criteria coverage

| ID | Ticket | AC | Phase | Verified by | Deviation |
```

**Give every row a stable ID** — `AC1`, `AC2`, … in table order, unique across the whole
document even when the plan covers several tickets. `implement-phases` copies these rows
into `.claude/state/current-plan.json` and reports met/unmet against them at every phase
boundary, so the ID is what lets a status report name a criterion without restating it.
IDs are assigned once and never renumbered: if review adds a clause, it takes the next
unused number wherever it sits in the table.

**One row per AC clause, not per AC theme.** Split on commas and semicolons: each clause
can be independently forgotten, and a theme-level row lets one vanish without leaving a
visible hole. Any clause whose phase cell you cannot fill is a gap in the plan, not a gap
in the table.

**Each NFR line is a row too.** The `## Non-functional requirements` lines of a covering
Epic or Story are criteria like its ACs: each takes the next `AC<n>` ID, with
`NFR<n>: <text>` in the `AC` column and its `[verify:]` tag's tier in `Verified by`, as
for an AC. So is a parent-Epic NFR this branch affects — any whose `NFR coverage` row is
not `untouched`. A threshold no phase meets is the same gap.

**`Verified by` is mandatory** and names which tier covers the clause. The project's tiers
are in `{{verification_tiers}}` — typically a named test, and, where the automated suite
cannot reach the behavior, an out-of-band session. A behavior's math being tested and the
behavior being correct are different claims; a plan that blurs them promises coverage it
will not deliver.

Use `Deviation` wherever the plan ships something other than what the AC literally says,
with a one-line reason. A reader checking coverage must see every departure from this table
alone, without reading the prose.

If a covering ticket has no Acceptance Criteria at all, say so here rather than writing
criteria for it. Inventing ACs produces a run that reports green against a bar nobody set —
raise the gap with Rob, per `CLAUDE.md`'s rule that every ticket carries them.

````markdown
## Approach

**The survey first**: two or three real implementations of the whole problem — not one
citation per component of a design already chosen. Then the chosen approach and which of
them it follows, or why it departs from all of them. Where an in-repo precedent or the
ticket's own design exists, cite it (`file:line`) and say how it compares to the survey; one
matching nothing surveyed is local invention, and saying so is the finding. Where nothing
external fits, mark it `waived` and raise it as an open question for Rob — never settle it
in the plan alone.

`implement-phases` copies the survey and the choice into `citations[]` at Step 1, and
`/ci-green` reports them at the end of delivery alongside every later one — so the
implementation chosen here is the one the whole run is measured against.

## Components and interfaces

```mermaid
flowchart LR
  <module> --> <module or new package it depends on>
```

### <module>

- Responsibility: <one sentence>
- Inputs: <what it accepts, and from whom>
- Outputs: <what it returns or emits>
- Errors: <each failure, and how a caller sees it>
- Versioning: <how the interface changes without breaking its callers>

## Likely changes

- <decision likely to change> — hidden behind <one interface>

## Data ownership

| Store | Owning module |

## Test strategy

| Level | Risks covered |
| unit | |
| integration | |
| system | |
| acceptance | |

Coverage target: <the number, and what it measures>

## NFR coverage

| Ticket | NFR | Design element |
| <TICKET-N> | NFR1 | <module>: <the mechanism in it that meets the threshold> |
| <EPIC-N> | NFR1 | untouched — <why this branch leaves its metric alone> |

## Threat model

| Component | Category | Rating | Mitigating phase |
| <module> | Spoofing | High | <N> |
| <module> | Tampering | Low | — |

## Rejected alternatives

Each with the reason it loses — including every surveyed implementation not chosen. If the
simplest approach is rejected, say why.

## Phases

### Phase N — <name>

- Files touched
- Change summary
- Tests added or updated
- Commit message

Each phase must be independently committable and leave the branch coherent — which means
**it builds on its own**. A phase referencing a type, case, or function a later phase
introduces does not build, and the claim is then false.

## Risks and open questions

## Ticket gaps
````

The five sections from `Components and interfaces` to `NFR coverage` carry rule book Phase
3 steps 1–3, 5 and 7 and its NFR exit criterion. `Components and interfaces` opens with a
flowchart of every module the plan changes, or an NFR row relies on, and what each depends
on, any new package included, then gives each module all five fields. Each `Likely changes`
entry names one interface; a decision spread across two is not hidden. `Data ownership`
names one owning module per store the plan touches. `Test strategy` names the risks each
level covers, or `none` and a reason in that level's row, and a coverage target saying what
it counts. `NFR coverage` has one row per ticket and `NFR<n>` pair, across the covering
tickets and their parent Epic, and each row traces to a module in `Components and
interfaces` and the mechanism in it that meets the threshold. A parent-Epic NFR this branch
does not affect reads `untouched — <reason>` instead. The AC table says which phase meets a
threshold; this one says which design element does.

**Any of these five sections with nothing to list holds `none` and a one-line reason** —
`none — no data store is touched` — never an empty heading, which reads the same as a
forgotten one. `Ticket gaps` keeps its own rule below.

**`Threat model` is required when `{{disciplines}}` contains `security`, and omitted
otherwise** — rule book Appendix B1. For each component in `Components and interfaces` that
handles external input, credentials, or personal data, it has six rows, one per STRIDE
category: `Spoofing`, `Tampering`, `Repudiation`, `Information disclosure`, `Denial of
service`, `Elevation of privilege`. Each is rated `High`, `Medium` or `Low`, and each `High`
row names the number of the phase that mitigates it. One line above the table names each
other component and why it handles none of those; with no qualifying component the section
holds `none — <reason>`.

`Ticket gaps` lists each place a covering ticket, as written, made this plan propose a
split, add a `Deviation` row, or hold an AC clause or NFR line with no fillable phase —
one line each, naming the ticket, the gap, and the `write-tickets` rubric criterion it falls
under. Omit the section when there are none. `implement-phases` copies it into `friction[]`.

The architecture rules the plan must respect are in `CLAUDE.md` and
`{{plan_rules_file}}`. Read them rather than working from memory.

### Size: at most 6 phases and `{{pr_review_limit_lines}}` changed lines; 500 plan lines outside the AC, NFR coverage and threat tables

**The phase count is the real limit.** A branch needs at most six phases; more than that is
a branch too large to review in one sitting, and the fix is splitting the work across PRs,
not writing tighter. Propose the split to Rob and let him choose — his answer may well be
one PR anyway, and then the justification goes in `Rejected alternatives`. Do not silently
compress seven phases into six. Unlike a line count this cannot be satisfied by compressing
prose, which is why it comes first.

**`{{pr_review_limit_lines}}` changed lines per PR** — insertions plus deletions, the size
rule book R9 says reviews in under an hour; the pre-push checklist checks it. Where the
phases will exceed it, propose the split here: sequenced PRs, or shipping unfinished
behavior dark behind a feature flag so each PR merges on its own. Under `none` there is no
line limit, and self-check item 10 is skipped.

**500 lines for the document, counting everything except the acceptance-criteria, `NFR
coverage` and `Threat model` tables.** Each is one row per clause, NFR line or STRIDE
category by design. A plan covering several tickets can carry thirty AC rows before a
single phase is written, and a security plan six threat rows per component — counting them
would penalize the splitting rule and the threat model's completeness. Everything else
counts.

**5 lines for `Change summary`.** This is the field that actually overflows, so it is the
field with the limit. What changes, and why, in five lines or fewer. If a claim needs three
paragraphs of defense, the approach is wrong or unverified — that is a signal to re-examine
it, not to write more words. Argument belongs in `Approach` and `Rejected alternatives`,
which are prose by design and uncapped.

`Files touched` has no line limit. A registry edit must enumerate its consumers, and that
list is sometimes long; truncating it to hit a number would defeat the rule requiring it.

**A phase is bullets, never paragraphs.** A phase running past ~40 lines with a five-line
`Change summary` and a legitimately long `Files touched` is fine. One running past 40
because its prose sprawls is a phase doing too much — **split it or cut its scope; do not
compress the prose to fit.**

### Describe the end state, never the revision history

The plan says what will ship. It does not narrate how the plan got here. Never write "an
earlier draft said…", "this was previously scoped as…", or "round N found…". When review
changes something, **edit it in place so the document reads as if it were always right**,
and carry the correction into every other passage stating the same fact — a corrected claim
left standing in three other paragraphs is how a plan starts contradicting itself.

Revision history belongs in chat, where Rob can see the reasoning moved. In the document it
is pure bulk, and it actively causes defects: every restatement of a fact is another copy to
drift.

### Verify claims instead of arguing for them

A plan asserting "safe by construction", "closes the class", "transcribed flag-for-flag", or
"exhaustive" must have run something that shows it. Fluent prose is where a
plausible-but-wrong claim survives — a shell command settles it in seconds and a paragraph
never does.

Prefer a guard that enumerates instances over a hand-maintained list of them: a list is a
count you will get wrong, a guard is one the repo reports. Where a claim genuinely cannot be
checked before implementation, mark it unverified in one clause and move on. Do not
compensate with length.

Do not default to the simplest, quickest, or easiest solution: choose from the survey or
justify departing from it, and where a simpler option loses, reject it in `Rejected
alternatives` with the reason. The simple option and the surveyed one are frequently the
same answer, and when they are, that is the answer — this rule exists to stop expedience,
not to buy elaboration. If you catch yourself writing "wait", "actually", or "let me look
at this differently" more than once, stop and think it through rather than iterating in the
open.

**Scope exclusions are decided here, with Rob, not later on your own.** If exploration finds
instances of a root cause the plan otherwise fixes, "What explicitly does not ship" must list
each one with a one-line reason. List them all: the value is that Rob sees the full spread
before approving, and an instance you found and did not mention is the one real failure here.

The reason may be that the instance is benign in context, and it may equally be that
covering it would make the branch too large to review. Both are legitimate, and this is the
moment to say which. What is not legitimate is discovering the instance and leaving it out
of the list.

This is the right moment to split work: if covering every instance would make one branch too
large to review, propose sequenced tickets in the plan and let Rob choose. Do not create
those tickets yet — deciding mid-implementation to file a follow-up instead of fixing is the
failure this exists to prevent.
When Rob chooses a split, `/write-tickets` with the covering keys rewrites them as the
sequence he chose.

## Step 5 — Self-check, then adversarial design review

### Before launching the reviewer, verify your own claims

The reviewer's scarcest output is the finding you could not have found yourself. Spending a
round on a claim one grep would have settled wastes it. Walk the finished plan and, for each
item below, either fix it or satisfy yourself it holds:

1. **Every "X currently does Y" claim about existing behavior** — name the command you ran.
   A claim about what a schema validates, what a test asserts, or what a CI filter matches
   is checkable in seconds, and stating one from memory is how a plan argues confidently for
   the wrong design. Where a claim rests on something being _absent_, grep for it and count:
   absence is a claim like any other.
2. **Every registry the plan edits** — the Step 3 grep was run and its consumers are listed
   in the phase that edits it.
3. **Every AC clause and NFR line the AC table takes** — has a row, a phase, and `Verified by`.
4. **Every cross-phase reference** — a phase naming a function, error code, or type that a
   later phase introduces does not build on its own; either move it or reorder.
5. **Every "independently committable" claim** — pick the phase you are least sure of and
   ask what `{{build_command}}` does on it alone.
6. **The whole problem, not each component** — ask what real systems solve the problem
   this plan solves, and whether `Approach` names two or three of them. A citation for every
   piece of a design taken from the ticket or the repo does not answer it. Local precedent
   is the harder case, not the safer one: following a pattern nobody can source is how a
   non-standard design spreads unremarked. Name the survey in `Approach`, or carry the
   no-fit to Rob as an open question marked `waived`.
7. **Every NFR in the covering tickets and their parent Epic** — has an `NFR coverage` row
   naming a module from `Components and interfaces`, or for an Epic NFR this branch does
   not affect, `untouched — <reason>`.
8. **All five design sections are present** — each filled, or `none — <reason>`.
9. **`Threat model` matches `{{disciplines}}`** — present with six rated rows per qualifying
   component and a phase on every `High` when it contains `security`, absent when it does not.
10. **The phases fit `{{pr_review_limit_lines}}`** — or the plan proposes the split.

Findings from this pass are edited in place, silently. They never appear in the plan as
revision history.

### Then launch the review

Launch the `design-adversary` subagent.

**The first delegation prompt contains only:** the path to the plan file, and the ticket
IDs. Nothing about why you chose the approach, nothing you learned during exploration,
nothing about what you expect it to find. It reviews the plan as written, cold.

Fix every BLOCKER, and fix the MAJORs you agree with. **MAJORs do not trigger another
round** — they get one pass, and a MAJOR you disagree with is noted in chat at Step 6, not
argued with the reviewer.

Re-run only if the round returned BLOCKERs. The second delegation adds exactly one
sentence — that the plan is a revision of one already reviewed — and still carries no
findings list, no summary of what you changed, and no defense of it. The reviewer stays
blind, per `deliver`'s invariant; it is told a round happened, never what it said.

**Two rounds, not three.** Every round rewrites the document in place, so a third is paid
for in full rewrites and lands almost entirely on prose the first two rounds wrote. The
kit-wide cap is three; this loop's is two, deliberately. If BLOCKERs persist after the
second, stop and bring the disagreement to Rob rather than continuing to iterate.

### A finding is fixed inside this plan, or it goes to Rob

**No finding may be resolved by deferring the work.** Not by creating a follow-up ticket,
not by proposing a split, not by moving an item into "what explicitly does not ship", not by
adding a `Deviation` row that narrows the scope. Those are scope decisions, and per Step 4
scope decisions are Rob's.

For each finding there are exactly two legal moves:

1. **Fix it in the plan** — change the approach, add the phase, correct the claim, reorder
   the phases. The plan gets better and the scope stays put.
2. **Carry it to Rob** as an open question, stated in one line with the reviewer's finding
   attached, and let him decide. Then stop and wait, as at Step 6.

A round whose fixes are predominantly deferrals has not improved the plan — it has moved
work out of view and left the document reading as if the work were done. If you find
yourself writing a follow-up ticket to satisfy a reviewer, that is the signal: the finding
belongs in front of Rob, not in a ticket you filed to clear it.

A MINOR you disagree with needs no ticket and no escalation. Note the disagreement in one
line when you present, and move on.

## Step 6 — Present for approval

Present in chat, concisely:

- The resolved ticket set, and the label it came from if applicable
- The phase list with one line each
- The approach: the implementations surveyed, the one it follows, how the in-repo precedent
  compares, and any `waived` no-fit as a decision for Rob
- **Which ACs need out-of-band verification**, called out separately — work `{{roles.qa}}`
  does personally, which the approver needs to know of now, not at ship time
- `## Test strategy`, for `{{roles.qa}}` to approve
- What the adversarial review found and what changed as a result
- Open questions needing a decision

Ask `{{roles.qa}}` to approve `## Test strategy`, and revise any part QA rejects. Then stop
and wait for `{{roles.tech_lead}}`, the gate's one accountable role in RACI terms, whose
approval counts only once QA has approved; one person holding both roles gives both in one
answer. Print both per `gates/project-config.md`. Any edit after Step 5, whoever asks for
it, re-runs Step 5's self-check and one `design-adversary` revision round outside its
two-round count; a BLOCKER from it goes to `{{roles.tech_lead}}`, and an edit to
`## Test strategy` goes back to QA, as a new commit dismisses a stale approval. Do not begin
implementation, do not create the branch, do not transition Jira. Approval is an explicit
"approved", "do it", or equivalent — a clarifying question is not approval.
