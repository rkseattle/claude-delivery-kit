# Design exit — the rule book's Phase 3 gate at feature scale

Rule book Phase 3: "The architecture must be documented and reviewed before implementation
of the affected components begins." `plan-work` applies it to one handoff of tickets; this
gate applies it to a whole feature or epic, before its tickets are written. Its exit
criteria are the four below, quoted from
`${CLAUDE_PLUGIN_ROOT}/reference/software-engineering-rule-book.md`. Read this file before
writing, reviewing, or presenting a design, and check every rule against the design doc at
`{{design_dir}}/<slug>.md` — `<slug>` the design's title in lowercase kebab-case — its
ADRs under `{{adr_dir}}`, and the repository, its git history included — never against
memory of what was written. With `{{design_dir}}` `none` there is no design doc, and the
gate cannot pass; with `{{adr_dir}}` `none`, a design holding a `- Costly to reverse:`
line fails.

The sections build on the Kubernetes KEP template's — summary, motivation, goals and
non-goals, proposal, risks, test plan, rollout and rollback, drawbacks, alternatives — with
Google design docs' cross-cutting concerns and the Rust RFC template's prior art, each a
top-level section so a checker finds it by heading. Decision records follow MADR 4.0;
diagrams follow the C4 model, drawn in Mermaid `flowchart`, since Mermaid marks its own C4
syntax experimental.

## Exit criteria

- [ ] Component diagram and interfaces reviewed
- [ ] Decision records exist for irreversible choices
- [ ] Test strategy approved by QA
- [ ] Each non-functional requirement has a design element that addresses it

## What settles each one

1. **Component diagram and interfaces reviewed** — `## Components and interfaces` passes
   its rules below, and `## Decision` records the tech lead's approval after two reviews:
   - a cold review, given only the design doc's path — the reviewer reads the Epic its
     `Epic:` line names — ending with no open BLOCKER; and
   - rule book Phase 3 step 8's design review, by at least one engineer outside the
     immediate team, checked against the requirements and non-functional thresholds.

   The commit recording the decision carries a `Reviewed-by: <name>` trailer per step 8
   reviewer, the Linux kernel's and Gerrit's trailer, so `git log` holds who reviewed it.
   `<name>` is asked for in the session, never defaulted, since an outside reviewer holds
   no role; the kit records no email, so the trailer carries none. A project with no
   engineer outside the team records a rule-book exception for step 8, per
   `${CLAUDE_PLUGIN_ROOT}/gates/exceptions.md`, in `{{exceptions_log}}`; the criterion then
   passes on the cold review while that row is unexpired. The kit-wide step 8 row covers
   `plan-work` plans, never a design.
2. **Decision records exist for irreversible choices** — every `- Costly to reverse:` line
   in `## Proposal` names an ADR path that exists and passes the ADR rules below.
3. **Test strategy approved by QA** — `{{roles.qa}}` approved `## Test strategy`, and the
   approver is named in `## Decision`.
4. **Each non-functional requirement has a design element that addresses it** — every
   `## Non-functional requirements` line names a module `## Components and interfaces`
   defines and the mechanism in it, and a design with an `Epic:` line has a line for each
   of that Epic's NFR lines.

## Sections

The design doc opens with the front matter its ADRs carry — `status`, `date`, and
`decision-makers`, under the ADR rules below — then a `# <title>` line, the title its
`<slug>` is made from, then holds these `##` sections, in this order, and no other `##`
section:

1. `Summary`
2. `Motivation`
3. `Goals`
4. `Non-goals`
5. `Success measures`
6. `Current state`
7. `Survey`
8. `Options`
9. `Proposal`
10. `Components and interfaces`
11. `Likely changes`
12. `Data model and ownership`
13. `Non-functional requirements`
14. `Threat model` — present only when `{{disciplines}}` contains `security`; omitted
    otherwise
15. `Rollout and rollback`
16. `Observability`
17. `Test strategy`
18. `Drawbacks`
19. `Risks`
20. `Work plan`
21. `Open questions`
22. `Revision history` — present only once the design has been reopened; omitted otherwise
23. `Decision`

A section with nothing to list holds `none — <reason>`, never an empty heading, save where
a rule below requires content.

## Section rules

- **`Summary`** — what the feature is, in a paragraph. A design written from an Epic key
  opens with the line `Epic: <KEY>`.
- **`Goals`** — at least one outcome, one line each.
- **`Non-goals`** — passes criterion 2 of `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md`.
- **`Success measures`** — each line in the form
  `- SM<n>: <Measure>: <target> by <date or milestone>`, with `SM1`, `SM2`, … unique in the
  doc; a design with an `Epic:` line keeps the Epic's `SM<n>` IDs for its measures. Rule 2
  of `${CLAUDE_PLUGIN_ROOT}/skills/plan-project/SKILL.md` Step 2 applies to the
  text after `SM<n>: `: a line whose target holds no number is rejected, and a milestone
  stands where rule 2 names a date.
- **`Current state`** — the existing features and code the new one overlaps or depends on,
  each with the `file:line` or Jira key behind it.
- **`Survey`** — two or three real systems that solve the whole problem, each with a
  source: a URL, a standard's name and section, or a repository path.
- **`Options`** — at least two options besides doing nothing, plus doing nothing. Each
  states the reason it wins or loses.
- **`Proposal`** — the chosen option. Each choice that is costly to reverse is one line:

  ```markdown
  - Costly to reverse: <choice> — ADR: <path>
  ```

  `<path>` is the choice's ADR under `{{adr_dir}}`, relative to the project root, the
  folder holding `.claude/`, as every `project.json` path is, per the ADR rules below.
- **`Components and interfaces`** — opens with a C4 container-level diagram in a Mermaid
  `flowchart` block: one system, the applications and data stores inside it, and the
  people and systems it talks to. Then, for each container the feature changes, a C4
  component-level diagram in its own `flowchart` block, on which every module of that
  container appears with an edge to each module it depends on — rule book Phase 3 step 1.
  Then one `###` per module, each carrying the `Responsibility`, `Inputs`, `Outputs`,
  `Errors`, `Versioning`, and `Layer` lines in the form of the `Components and interfaces`
  template of `${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md`; `Layer` is rule book
  Phase 3 step 4, and a new or restructured module spanning two layers is two modules; an
  existing one keeps both, in `plan-work`'s `— existing` form.
- **`Likely changes`** — in the form of that template's `Likely changes` list.
- **`Data model and ownership`** — first the data model, rule book Phase 3 step 5: for each
  entity, store, or dataset the feature adds or changes, its fields, keys, and relations to
  other entities. Then a `Data ownership` table under that template's rule for it, its
  `data-ml` form, filled cells, and `none — <reason>` included, read for the feature in
  place of the plan.
- **`Non-functional requirements`** — each line
  `- NFR<n>: <threshold> — <module>: <mechanism>`, with `NFR<n>` unique in the doc. A
  design with an `Epic:` line carries one line per NFR line of that Epic, keeping its
  `NFR<n>`. `<threshold>` follows the threshold rule of
  `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md`: a comparator, then
  a number and its unit.

  In these three sections, each interface, owning module, or `<module>` named is a `###`
  of `Components and interfaces`, changed or not, so it appears on the diagram there too.
- **`Threat model`** — with `security` in `{{disciplines}}`, the STRIDE form of the
  `Threat model` section of `${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md`, with a
  `Mitigating handoff` column naming a `Work plan` handoff in place of `Mitigating phase`.
  Without `security`, the section is absent.
- **`Rollout and rollback`** — the rollout as numbered steps, each naming the rollback step
  that undoes it. A rollout step with no rollback step fails.
- **`Observability`** — how the feature's failures are seen: logs, metrics, or alerts.
- **`Test strategy`** — in the form of the `Test strategy` table and coverage-target line
  of `${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md`.
- **`Drawbacks`** — why the feature should not be built.
- **`Risks`** — passes criterion 3 of `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md`.
- **`Work plan`** — the handoffs, per the rules below.
- **`Open questions`** — each item one line. An approved design keeps an item only in the
  form `- <question> — Spike: <handoff>`, naming the `Work plan` handoff whose spike
  settles it.
- **`Revision history`** — one `- <YYYY-MM-DD>: <reason>` line per reopen, oldest first,
  the reason quoting the findings that reopened it.
- **`Decision`** — per the decision rules below.

## Work plan

One `###` per handoff, in build order:

```markdown
### Handoff: <label>

Delivers: SM<n>, SM<m>
Estimated changed lines: <n>

- <ticket summary>
  - Phase 1 — <name>
  - Phase 2 — <name>
- <ticket summary>
  - Phase 1 — <name>
```

- `<label>` is the handoff's name and a valid Jira label: no whitespace, at most 255
  characters. `plan-work` is run with it.
- `Delivers:` names the success measures the handoff delivers, by their `SM<n>` IDs, or
  reads `Delivers: none — enabling` when every ticket in it is enabling work, as rubric E3
  of `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/rubric.md` allows a child to
  map to no measure. Every `SM<n>` in `## Success measures` is named by at least one
  handoff.
- Each ticket is a `- <summary>` line followed by its phases, and the tickets are listed in
  build order.
- The handoff fits `plan-work`'s handoff limit, in its Step 1, and its phase limit, in its
  **Size** section, read from `${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md` so there is
  one number to change. The phase limit applies to the sum of the handoff's tickets' phases,
  since a handoff is one `plan-work` run. Over a limit, the handoff is split here, where the
  design is approved, so `plan-work` never has to propose the split.
- `Estimated changed lines:` is at most `{{pr_review_limit_lines}}`. Under `none` the line
  is omitted and no limit applies.

## ADRs

One ADR per `- Costly to reverse:` line, in MADR 4.0 form, at
`{{adr_dir}}/NNNN-<title>.md`. `<title>` is the choice in lowercase kebab-case, as MADR
names its files; `NNNN` is four digits.

- **Numbering, when the design's ADRs are written:** they take consecutive numbers in
  `## Proposal` order, starting one above the highest number under `{{adr_dir}}` on
  `origin/{{parent_branch_default}}`, read after `git fetch`, and in the working tree
  outside this design — as adr-tools numbers from the highest file present. Rework that
  adds or removes a `- Costly to reverse:` line renumbers the design's ADRs the same way;
  none is on `origin/{{parent_branch_default}}` yet, so no number is reused.
- **What criterion 2 checks:** each of the design's ADRs exists at the path its line
  names, their numbers are consecutive in `## Proposal` order, and none shares its number
  with another `<digits>-<title>.md` file directly under `{{adr_dir}}`, its digits read as
  a number, on the design's branch or on `origin/{{parent_branch_default}}`. Two designs
  in flight on different branches can take the same numbers, as with adr-tools, so
  `ci-green`'s merge step runs `${CLAUDE_PLUGIN_ROOT}/gates/scripts/adr_numbers.py`
  against the PR's base, failing a number one of the branch's added records shares with
  another record in the merged result.
- **A rejected design's ADRs** are committed with it, `status: rejected`, keeping their
  numbers, as a rejected brief is committed as the record of the stop.
- **Superseding is out of scope:** a design whose choice would reverse an `accepted` ADR
  fails criterion 2, since superseding one needs its own review and approval.

```markdown
---
status: proposed
date: <YYYY-MM-DD>
decision-makers: <tech lead>
---

# <short title of the problem and the solution>

## Context and Problem Statement

## Considered Options

## Decision Outcome

### Consequences
```

- `## Considered Options` lists at least two options.
- `### Consequences` lists the choice's good and bad consequences, as rule book R11
  requires; MADR makes it optional, this gate does not.
- `status` reads `proposed` until the design is decided, then `accepted` once the design is
  approved, or `rejected` once it is rejected. `date` is when the decision was last
  updated, as MADR defines it, so it changes with `status`.
- An ADR whose `- Costly to reverse:` line rework removes is deleted with it, before the
  decision; it was never on `origin/{{parent_branch_default}}`, so its number is free again.

## Approvers

`{{roles.tech_lead}}` is the accountable approver of the design. Before the tech lead
approves, `{{roles.qa}}` approves `## Test strategy` and `{{roles.product_owner}}` approves
`## Goals` and `## Non-goals`. A rejection from QA or the product owner is a request for
rework on the section they reject, not a decision; only the tech lead rejects a design.
The tech lead's answers are those of `plan-project` Step 4: approve, reject, rework, or
hold. An approval is given in the session and is written down only at Step 6, in `status`
and, naming its approvers, in `## Decision`, so a session that ends first asks again. An
edit to the design after a review re-runs that review, the cold one and step 8's alike; an
edit to an approved section voids that approval and goes back to its approver, as a new
commit dismisses a stale pull-request approval. A renumber under the ADR rules above changes
no choice, so it re-runs criterion 2's checks but no review, and voids no approval.

Each approver's name written below is the handle `roles` holds, or, for a role `roles`
leaves out, the git `user.name` of the person running the session — asked for when unset —
never the word "you", as `plan-project` writes its sponsor.

## Decision

Until the design is decided, `## Decision` reads:

```markdown
Pending — <tech lead>.
```

An approved design reads, naming each distinct approver among QA, the product owner, and
the tech lead once, in that order of first appearance, joined by `; `, with the date of the
tech lead's decision:

```markdown
Approved by <approver>; <approver> on <YYYY-MM-DD>.
```

An answer is relayed by `plan-project` Step 5's tests, read against the role it answered
for; a person holding several roles is relayed when any of their answers was. A relayed
approver takes Step 5's suffix,
`, relayed by <login, or git user.name>`, right after their name rather than before the
period, since with several approvers the suffix must say whose answer was relayed.
A rejected design reads `Rejected by <tech lead> on <YYYY-MM-DD>.`, with the same suffix
when relayed, followed by one line giving the reason.

The design's `status` moves with its ADRs': `accepted` with an approval, `rejected` with a
rejection, `date` the decision's date. A design is approved by its `status` alone, the
field `${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py design-read` checks, as kepval
reads a KEP's `status`; `## Decision` records who approved it.

## Status transitions

A design's `status` moves only by these, each but the first committed on `design/<slug>`,
or for a reopen `design/<slug>-rev<N>`, and merged by pull request, as a merged KEP is
revised: a draft's first `proposed`, in the working tree; a new design's `accepted` or
`rejected`; `proposed → accepted` or `rejected`; and the reopen `accepted → proposed`. Any
other move, or a decision or reopen on `{{parent_branch_default}}` itself, is invalid;
`${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py design-transition` checks it.
