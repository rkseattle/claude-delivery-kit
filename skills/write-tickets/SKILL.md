---
name: write-tickets
description: Turn a feature request, spec, bug report, or approved feature design into Jira epics, stories, tasks, and bugs that plan-work can plan without proposing a split, writing a Deviation, or leaving an AC clause unphased. Drafts to a file, lints it, has ticket-adversary review it cold, and creates the tickets only after approval.
argument-hint: <what to write tickets for> | <design path> | <TICKET-N ...> to rewrite existing ones
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

Write tickets for: $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/rubric.md` and
`${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md` before drafting.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` first: `{{ticket_prefix}}`,
`{{jira_project}}`, `{{registry_file}}`, `{{source_roots}}`, `{{verification_tiers}}`,
`{{plan_rules_file}}`, `{{build_command}}`, `{{parent_branch_default}}`, `{{brief_file}}`,
`{{disciplines}}`, `{{design_dir}}`, and `{{roles.*}}` all come from it. Read
`${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly.

No ticket is created, edited, or transitioned before Step 7's approval; until then it
writes only the draft and the input files of the checks it runs.

## Step 1 — Settle the decisions

State the requested outcome in one sentence. List every behavior-changing choice not yet
made: data format, error shape, UI copy, limits, library, owning layer. With a design, read
it first, as Step 2 says, and list only what it leaves open; Rob wanting a choice made
otherwise is design rework, for Step 6. Ask Rob all of them in one message and wait.

A choice that needs research becomes a spike Task (rubric R6). A choice cheap to reverse
takes a stated assumption, written in the ticket's Context, rather than a blocking question.

## Step 2 — Ground in the code

Survey the code before writing any AC. Delegate breadth to `Explore` subagents with
request-derived scope. Establish, by reading the code rather than file names:

- where each behavior lives, and the in-repo pattern for it
- that every function, type, route, table, and config key you will name exists and
  behaves as you will describe it
- **registry consumers**: for every shared symbol a ticket will edit, run
  `grep -rln "<SYMBOL>" {{source_roots}}` and keep the list; `{{registry_file}}` names the
  known registries and the consumer class each one hides
- **other instances of a root cause** the work fixes, by grep, not recall
- for each tier in `{{verification_tiers}}`, where its evidence lives: the test directory,
  one existing test, and the command that runs it
- **the brief's goals**, for `Goal:` lines: the `## Goals` that `python3
  "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" brief-read --config
  "<absolute project root>/.claude/project.json"` prints, or at `{{brief_file}}` `none`, a
  line saying so. On `INVALID:`, print it and its `NEXT:` line and stop. Stop too unless a
  goal names an outcome, never "none", "TBD", or "N/A": send that brief to
  `{{roles.sponsor}}` through `plan-project`. Relay a `DEPRECATED:` line to Rob.
- **the design** the request names by path: at `{{design_dir}}` `none`, stop and name the
  key. Write the path to a file per **Untrusted text**; stop if `git fetch origin
  {{parent_branch_default}}` fails. Run `lifecycle` on it, below; at any state but
  `design-accepted-on-parent` or `tickets-draft`, print its two lines and stop. Read the
  design and the Epic's `- Design:` path only from what `design-read` prints, the path with
  `--path`. Its `Work plan` is the slice: a Step 3 split, an added ticket, or a review
  finding changing a handoff's tickets is design rework, for Step 6.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" <lifecycle | design-read> --ref "origin/{{parent_branch_default}}" --config "<absolute project root>/.claude/project.json" < "<file>"
  ```

Then search Jira: `project = {{jira_project}}` with the request's key terms, for tickets
that overlap or that the new ones depend on. Record each one's key and status.

## Step 3 — Slice

In order:

1. One ticket, one behavior change that can merge alone without breaking the build.
2. Sketch each ticket's phases the way `plan-work` would. Any ticket whose sketch exceeds
   `plan-work`'s phase limit is split now, not after review.
3. Registry consumers from Step 2 are part of the ticket that edits the registry. When they
   push it past the limit, the split follows the consumers, not the layers.
4. Every live instance of a root cause is covered or excluded as benign in context; when
   covering all of them is too large, the sequence of tickets is the proposal Step 7 shows.
5. A prerequisite two tickets share — a migration, a new module, test infrastructure — is
   its own Task, labeled `enabling`.
6. Group tickets into handoffs under a `Handoff:` label, in build order, each group within
   `plan-work`'s handoff limit. With a design, each `Work plan` handoff is one group, named
   as the handoff, holding its tickets in its order.

## Step 4 — Draft

Write `docs/tickets/<slug>.md` (gitignored) in the templates' format, blockers before
dependents; revise a draft already there if it is this request's, or ask. `<slug>` is what
this prints for the request, fed per **Untrusted text** in `gates/project-config.md`; on
`INVALID:`, ask for Latin letters:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" draft-slug < "<request file>"
```

- **ACs**: concrete values, one verifiable clause per comma or semicolon, each ending
  `[verify: <tier> @ <evidence>]`. A clause only an out-of-band tier can settle is written
  that way on purpose, not dressed as automated.
- **Touch points**: every production file, registry consumers included, each marked
  `(modify)`, `(new)`, or `(delete)` with its purpose.
- **Out of scope**: adjacent work and its home; excluded instances with the benign claim.
- **Goal**, when Step 2 read the brief's goals: each `Goal:` line and Epic `## Goal`
  restates the one it serves; a ticket whose goal serves none is removed (R14).
- **Context**: why, with any linked source summarized. Never a reference to this session.
- **Design**: a design `## Summary` opening `Epic: <KEY>` names its Epic; stop unless the
  key, fed as Step 2 feeds the path, passes `project_rules.py ticket-key --prefix
  "{{ticket_prefix}}"` and the issue is an Epic. Fetch it and each not-Done child as Step 8
  fetches, and draft the rest as new under it. A not-Done child no design ticket's summary
  equals, or a design ticket a Done child's summary equals, is design rework, for Step 6.
  Otherwise draft a new Epic from the design's Goals, Success measures, NFR thresholds, and
  Non-goals. Either Epic carries templates.md's one `- Design:` line.

## Step 5 — Lint

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/scripts/lint_draft.py docs/tickets/<slug>.md --repo "<absolute project root>"
```

Fix every ERROR, and fix each WARN or confirm its text is concrete; re-run until exit 0.
Exit 2 stops. With a design, a group whose tickets differ from its handoff's in count,
summary, or order is design rework, for Step 6.

## Step 6 — Adversarial ticket review

Launch `ticket-adversary`. **The delegation prompt contains only the absolute path to the
draft.** It reads the tickets as `plan-work` will, cold; anything added is context it lacks.

Fix every BLOCKER and MAJOR in the ticket text. A finding that misread a ticket means the
ticket is ambiguous: fix the text, never explain it to the reviewer. Re-lint, re-review.
Stop at no BLOCKERs or three rounds, whichever is first; revert-not-iterate applies. At
the cap, bring the remaining findings to Rob. Append each round's output, and below it the
`<!--` lines Steps 7 and 8 add, under `<!-- review round N -->`, never sent to Jira.

**Design rework** — a change only the design can make: its `Work plan`, a Goal, an NFR, or
a premise it states. On one, from any step, stop. Write `<!-- design-rework: <ticket IDs> @
<blob> -->` at the draft's end, `<blob>` what `git rev-parse
"origin/{{parent_branch_default}}:<design path>"` prints, so a revised design voids it.
Before Step 4, first write the draft as its Epic header and `- Design:` line alone.
Bring Rob the findings, then print `NEXT: /delivery-kit:design-feature <Epic key or path>`.

## Step 7 — Present for approval

In chat, one table — ID, type, summary, priority, severity, handoff, AC clauses, touch
points, blocked by — then:

- clauses that need out-of-band verification, called out separately
- each ticket Step 4 removed for serving no goal of the brief
- each fetched ticket's labels other than `moscow-*`, `severity-*`, and its `Handoff:`; one
  Rob names stale moves from its `Labels:` to a `<!-- stale label: <key> <label> -->` line
- any sequenced split from Step 3, and every DECISION from the review
- assumptions stated in place of questions

Ask `{{roles.qa}}` to confirm every `Priority: Must` ticket's ACs are testable, fixing any
that are not, then wait for `{{roles.product_owner}}`, whose approval counts only after
QA's; one person in both roles gets one question. Print each per `gates/project-config.md`.
An edit after Step 6 re-runs Step 5 and one Step 6 round outside its count; its BLOCKERs go
to the product owner, and an edit to a `Must` ticket's ACs goes back to QA, as a new commit
dismisses a stale approval. Approval is an explicit "approved" or "create them", never a
clarifying question.

## Step 8 — Create

Look up issue and link types via the Atlassian MCP first; never guess a name or ID.
Journal each create in a `<!-- creating: <ID> -->` line that item 5 removes. Resuming a
stopped run, search by exact summary for each journaled ticket; a match takes item 5. A
ticket with `Jira:` filled and `Baseline:` empty is updated as items 2–3 write it, given
only item 4's missing links, and item 6, with no Change impact.

1. Epics first, then the rest in draft order.
2. Summary, parent, and labels: every `Labels:` value, the `Handoff:` label, for a
   non-empty `Priority:`, `moscow-<priority>` in lowercase — `Won't` is `moscow-wont` —
   and for a Bug, `severity-<severity>` in lowercase.
3. Description: `Goal: <sentence>` first when the header has one, then every `##` section
   except Open questions, Change impact, review output, and comments, with each
   `[verify: …]` and `[children: …]` tag inside a code span, which the connector's read
   conversion keeps.
4. For each Blocked-by entry, a link of the blocking type with the blocker as outward.
5. After each creation, write the key into its `Jira:` line and replace its local ID with
   the key everywhere in the draft — as a whole ID, never the `S1` in `S10` — before
   creating the next ticket.
6. Read each ticket back with `jira_get_issue`, which returns Markdown. Check it carries
   every label item 2 names and no other `moscow-*`, `severity-*`, handoff, or its stale label,
   save its description verbatim to `docs/tickets/<slug>.<key>.md`, and run:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/scripts/lint_draft.py \
     docs/tickets/<slug>.md --readback <key> docs/tickets/<slug>.<key>.md
   ```

   On exit 1, update the description once and run it again. A second exit 1 is damage a
   re-push cannot repair: stop and bring Rob the `MISSING` lines. Exit 2 means the draft
   or saved file is unreadable, or nothing in the draft names the key. Delete the saved
   copy once it exits 0.
7. A ticket created before one it names — an epic's `[children: …]` and `## Children`, an
   Out of scope or Dependencies line naming a later sibling — went to Jira holding that
   local ID. Once every ticket exists, update each ticket whose draft text item 5 changed
   after its creation, and give it item 6 again.

Fetch each `<TICKET-N ...>` argument and Step 4's fetched tickets into the draft, its key as
header ID and on `Baseline:` and `Jira:`, so no local ID stands for an existing issue:

- its one `moscow-*` label to `Priority:`, title-cased, `moscow-wont` as `Won't`; and on a
  Bug its one `severity-*` label to `Severity:`, title-cased. None, or more than one, leaves
  the header empty for Step 1 to settle
- every other label but a handoff label, as defined below, to `Labels:` — never a
  `moscow-*` or `severity-*` label, which only the two headers above carry
- a leading `Goal:` description line to the `Goal:` header
- a code span holding a whole `[verify: … @ …]` or `[children: …]` tag, or the
  `\verify: …\` an older write left, to the bare tag

Run Steps 2–7 for `<TICKET-N ...>` arguments. A ticket whose `Baseline:` is filled is
updated, not created. Item 2's labels replace its `moscow-*`, `severity-*`, and handoff
labels — one equal to a draft `Handoff:` or design `Work plan` label, or one its
`stale label` line names — and every other label stays. It carries `## Change impact`
(rubric R15). After item 7, post each note once with `jira_add_comment`: `Change impact`,
then the section's lines, tags in code spans as in item 3. Only a returned comment ID
confirms a post; never retry one, since it may have landed. Any stop after the first update
brings Rob every unconfirmed note. A ticket that must split keeps its key for the ACs it
retains; say which new key holds the rest. Every run ends Step 8 by appending
`<!-- tickets created -->` to the draft, which `lifecycle` reads as Step 8 finished.

## Step 9 — Report

Keys with summaries and URLs, handoff labels in order, the first handoff's `plan-work` call.
