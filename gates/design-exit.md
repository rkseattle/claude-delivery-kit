# Design exit — the rule book's Phase 3 gate at feature scale

Rule book Phase 3: "The architecture must be documented and reviewed before implementation
of the affected components begins." `plan-work` applies it to one handoff of tickets; this
gate applies it to a whole feature or epic, before its tickets are written. Its exit
criteria are the four below, quoted from
`${CLAUDE_PLUGIN_ROOT}/reference/software-engineering-rule-book.md`. Read this file before
writing, reviewing, or presenting a design, and check every rule against the design doc at
`{{design_dir}}/<slug>.md` — `<slug>` the design's title in lowercase kebab-case — its ADRs
under `{{adr_dir}}`, and the repository, its git history included — never against memory of
what was written. With `{{design_dir}}` `none` there is no design doc, and the
gate cannot pass; with `{{adr_dir}}` `none`, a design holding a `- Costly to reverse:` line
fails.

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

   The commit recording the decision carries a `Reviewed-by: Name <email>` trailer per
   step 8 reviewer, the Linux kernel's and Gerrit's form, so `git log` holds who reviewed
   it. A project with no engineer outside the team records a rule-book exception for step
   8, per `${CLAUDE_PLUGIN_ROOT}/gates/exceptions.md`, rather than passing this criterion.
2. **Decision records exist for irreversible choices** — every `- Costly to reverse:` line
   in `## Proposal` names an ADR path that exists and passes the ADR rules below.
3. **Test strategy approved by QA** — `{{roles.qa}}` approved `## Test strategy`, and the
   approver is named in `## Decision`.
4. **Each non-functional requirement has a design element that addresses it** — every
   `## Non-functional requirements` line names a module `## Components and interfaces`
   defines and the mechanism in it, and a design with an `Epic:` line has a line for each
   of that Epic's NFR lines.

## Sections

The design doc opens with a `# <title>` line, the title its `<slug>` is made from, then
holds these `##` sections, in this order, and no other `##` section:

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
22. `Decision`

A section with nothing to list holds `none — <reason>`, never an empty heading, save where
a rule below requires content.

## Section rules

- **`Summary`** — what the feature is, in a paragraph. A design written from an Epic key
  opens with the line `Epic: <KEY>`.
- **`Goals`** — at least one outcome, one line each.
- **`Non-goals`** — passes criterion 2 of `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md`.
- **`Success measures`** — each line in the form
  `- SM<n>: <Measure>: <target> by <date or milestone>`, with `SM1`, `SM2`, … unique in the
  doc. Rule 2 of `${CLAUDE_PLUGIN_ROOT}/skills/plan-project/SKILL.md` Step 2 applies to the
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

  `<path>` is the choice's ADR under `{{adr_dir}}`, relative to the repository root, per
  the ADR rules below.
- **`Components and interfaces`** — opens with a C4 container-level diagram in a Mermaid
  `flowchart` block: one system, the applications and data stores inside it, and the
  people and systems it talks to. Then, for each container the feature changes, a C4
  component-level diagram in its own `flowchart` block, on which every module of that
  container appears with an edge to each module it depends on — rule book Phase 3 step 1.
  Then one `###` per module, each carrying the `Responsibility`, `Inputs`, `Outputs`,
  `Errors`, `Versioning`, and `Layer` lines in the form of the `Components and interfaces`
  template of `${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md`; `Layer` is rule book
  Phase 3 step 4, and a module spanning two layers is two modules.
- **`Likely changes`** and **`Data model and ownership`** — in the form of that template's
  `Likely changes` list and `Data ownership` table, one row per store the feature touches.
- **`Non-functional requirements`** — each line
  `- NFR<n>: <threshold> — <module>: <mechanism>`, with `NFR<n>` unique in the doc. A
  design with an `Epic:` line carries one line per NFR line of that Epic, keeping its
  `NFR<n>`. `<threshold>` follows the threshold rule of
  `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md`: a comparator, then
  a number and its unit.

  In these three sections, each interface, owning module, or `<module>` named is a `###`
  of `Components and interfaces`.
- **`Threat model`** — with `security` in `{{disciplines}}`, the STRIDE form of the
  `Threat model` section of `${CLAUDE_PLUGIN_ROOT}/skills/plan-work/SKILL.md`, with a
  `Mitigating handoff` column naming a `Work plan` handoff in place of `Mitigating phase`.
  Without `security`, the section is absent.
- **`Rollout and rollback`** — the rollout as numbered steps, each naming the rollback step
  that undoes it. A rollout step with no rollback step fails.
- **`Observability`** — how the feature's failures are seen: logs, metrics, or alerts.
- **`Test strategy`** — which levels (unit, integration, system, acceptance) cover which
  risks, and the coverage target with what it counts.
- **`Drawbacks`** — why the feature should not be built.
- **`Risks`** — passes criterion 3 of `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md`.
- **`Work plan`** — the handoffs, per the rules below.
- **`Open questions`** — each item one line. An approved design keeps an item only in the
  form `- <question> — Spike: <handoff>`, naming the `Work plan` handoff whose spike
  settles it.
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
  since a handoff is one `plan-work` run.
- `Estimated changed lines:` is at most `{{pr_review_limit_lines}}`. Under `none` the line
  is omitted and no limit applies.

## ADRs

One ADR per `- Costly to reverse:` line, in MADR 4.0 form, at
`{{adr_dir}}/NNNN-<title>.md`. `<title>` is the choice in lowercase kebab-case, as MADR
names its files. `NNNN` is four digits, the next number unused under `{{adr_dir}}` on
`origin/{{parent_branch_default}}` and in the working tree — one above the highest in
either, as adr-tools numbers from the highest file present — and a design's own ADRs take
consecutive numbers in `## Proposal` order. `origin/{{parent_branch_default}}` is read
after `git fetch`. Criterion 2 fails a design whose ADR shares its number with any other
file under `{{adr_dir}}`, on its branch or on `origin/{{parent_branch_default}}`.

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
```

- `## Considered Options` lists at least two options.
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
hold. An approval is given in the session and is written down only in `## Decision`, so a
session that ends first asks again. An edit to the design after its cold review re-runs
the review; an edit to an approved section voids that approval and goes back to its
approver, as a new commit dismisses a stale pull-request approval.

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
