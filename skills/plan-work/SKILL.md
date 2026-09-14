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

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` first: `{{ticket_prefix}}`,
`{{jira_project}}`, `{{registry_file}}`, and the build command below all come from it.

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

Fetch each resolved ticket and read the full description and acceptance criteria **before
launching anything else**. Do not parallelize the fetch with exploration. The session
context contains recent git commits, and launching an exploration agent before the ticket
content is known anchors it on the wrong domain — this has happened.

Read linked and blocking tickets too. Cross-story dependencies are often written in prose
inside descriptions rather than as Jira links, so read the descriptions for sequencing
constraints rather than relying on link metadata.

## Step 3 — Explore the codebase

Now, and only now, survey the code. Delegate breadth to `Explore` subagents so the survey
does not consume the main context; run several in parallel across distinct questions. Give
each one ticket-derived scope, not commit-derived scope.

Establish:

- Where the affected domain currently lives — which directories and which specific files
- The established in-repo pattern for the thing being built. If the repo already solves
  this problem somewhere, the plan follows that solution.
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

```markdown
## Approach

The chosen approach, and why it is the standard one for this problem — name the pattern.
**Cite the exemplar it comes from outside this repo**: the documented standard, framework
convention, or well-known implementation it is an instance of. Where an in-repo precedent
exists, cite it as `file:line` as well — but a precedent you cannot also name externally is
local invention, and saying so is the finding. Where no external exemplar applies, say that
in one line and why. Where this departs from precedent, say so and justify it.

`implement-phases` copies this citation into `citations[]` in the state file at Step 1, and
`/ci-green` reports it at the end of delivery alongside every later one — so the standard
named here is the one the whole run is measured against.

## Rejected alternatives

Each with the reason it loses. If the simplest approach is rejected, say why.

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
```

The architecture rules the plan must respect are in `CLAUDE.md` and
`{{plan_rules_file}}`. Read them rather than working from memory.

### Size: at most 6 phases, 500 lines outside the AC table

**The phase count is the real limit.** A branch needs at most six phases; more than that is
a branch too large to review in one sitting, and the fix is splitting the work across PRs,
not writing tighter. Propose the split to Rob and let him choose — his answer may well be
one PR anyway, and then the justification goes in `Rejected alternatives`. Do not silently
compress seven phases into six. Unlike a line count this cannot be satisfied by compressing
prose, which is why it comes first.

**500 lines for the document, counting everything except the acceptance-criteria table.**
That table is one row per AC clause by design, and a plan covering several tickets can carry
thirty rows before a single phase is written — counting it would penalize the splitting rule
above it. Everything else counts.

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

Never the simplest, quickest, or easiest solution. If you catch yourself writing "wait",
"actually", or "let me look at this differently" more than once, stop and think it through
rather than iterating in the open.

**Scope exclusions are decided here, with Rob, not later on your own.** If exploration finds
instances of a root cause the plan otherwise fixes, "What explicitly does not ship" must list
each one and justify it as **benign in context** — it cannot produce a wrong result for any
user or any test. A different feature, view, service, or workspace is not a justification,
and neither is "the automated suite cannot reach it". `design-adversary` will evaluate each
exclusion on that bar.

This is the right moment to split work: if covering every instance would make one branch too
large to review, propose sequenced tickets in the plan and let Rob choose. Do not create
those tickets yet — deciding mid-implementation to file a follow-up instead of fixing is the
failure this exists to prevent.

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
3. **Every AC clause** — has a row, a phase number, and a `Verified by` value.
4. **Every cross-phase reference** — a phase naming a function, error code, or type that a
   later phase introduces does not build on its own; either move it or reorder.
5. **Every "independently committable" claim** — pick the phase you are least sure of and
   ask what `{{build_command}}` does on it alone.
6. **Every component whose `Approach` cites no external exemplar** — search for the
   established approach before designing one. An empty prior-art grep means no _local_
   precedent, not that none exists, and a component with local precedent is the harder
   case, not the safer one: following a pattern nobody can source is how a non-standard
   design spreads unremarked. Name the standard in `Approach`, or say in one line why none
   applies here.

Findings from this pass are edited in place, silently. They never appear in the plan as
revision history.

### Then launch the review

Launch the `design-adversary` subagent.

**The delegation prompt contains only:** the path to the plan file, and the ticket IDs.
Nothing about why you chose the approach, nothing you learned during exploration, nothing
about what you expect it to find. It reviews the plan as written, cold.

Fix every BLOCKER and MAJOR, then re-run the review on the revised plan. Repeat until it
returns no BLOCKERs, to a maximum of three rounds. If BLOCKERs persist after the third, stop
and bring the disagreement to Rob rather than continuing to iterate.

## Step 6 — Present for approval

Present in chat, concisely:

- The resolved ticket set, and the label it came from if applicable
- The phase list with one line each
- The approach and its justification, with the in-repo precedent cited
- **Which ACs need out-of-band verification**, called out separately — that is work Rob has
  to do personally, and he needs to know before approving, not at ship time
- What the adversarial review found and what changed as a result
- Open questions needing a decision

Then stop and wait. Do not begin implementation, do not create the branch, do not transition
Jira. Approval is an explicit "approved", "do it", or equivalent — a clarifying question is
not approval.
