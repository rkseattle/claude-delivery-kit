---
name: write-tickets
description: Turn a feature request, spec, or bug report into Jira epics, stories, tasks, and bugs that plan-work can plan without proposing a split, writing a Deviation, or leaving an AC clause unphased. Drafts to a file, lints it, has ticket-adversary review it cold, and creates the tickets only after approval.
argument-hint: <what to write tickets for> | <TICKET-N ...> to rewrite existing ones
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

Write tickets for: $ARGUMENTS

This skill produces tickets that the next stage can plan as written. `plan-work` is where a
loose ticket turns into a split proposal, a `Deviation`, or a clause with no phase; the
rubric at `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/rubric.md` lists what
prevents each one. Read it and
`${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md` before drafting.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` first: `{{ticket_prefix}}`,
`{{jira_project}}`, `{{registry_file}}`, `{{source_roots}}`, `{{verification_tiers}}`,
`{{plan_rules_file}}`, `{{build_command}}`, and `{{parent_branch_default}}` all come from
it. If it is absent, stop and say so — tickets written against invented tiers and roots
fail at `plan-work` for reasons nobody can see.

No ticket is created, edited, or transitioned before Step 7's approval. The only file this
skill writes before then is the draft.

## Step 1 — Settle the decisions

State the requested outcome in one sentence. Then list every choice that changes behavior
and is not yet made: data format, error shape, UI copy, limits, library, which layer owns
the logic. Ask Rob all of them in one message and wait.

A choice that needs research to make becomes a spike Task (rubric R6), not a question in a
ticket. If a choice is cheap to reverse, prefer a stated assumption to a blocking question,
per `deliver`'s invariants — and put the assumption in the ticket's Context.

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

Then search Jira: `project = {{jira_project}}` with the request's key terms, for tickets
that overlap or that the new ones depend on. Record each one's key and status.

## Step 3 — Slice

In order:

1. One ticket, one behavior change that can merge alone without breaking the build.
2. Sketch each ticket's phases the way `plan-work` would. Any ticket whose sketch exceeds
   `plan-work`'s phase limit is split now, not after review.
3. Registry consumers from Step 2 are part of the ticket that edits the registry. When they
   push it past the limit, the split follows the consumers, not the layers.
4. Every live instance of a root cause is covered or excluded as benign in context. When
   covering all of them is too large, the sequence of tickets is the proposal — Step 7
   puts it to Rob.
5. A prerequisite two tickets share — a migration, a new module, test infrastructure — is
   its own Task, labeled `enabling`.
6. Group tickets into handoffs under a `Handoff:` label, in build order, each group within
   `plan-work`'s handoff limit.

## Step 4 — Draft

Write `docs/tickets/<slug>.md` — gitignored working state, like `docs/plans/` — in the
templates' format, blockers before dependents.

- **ACs**: concrete values, one verifiable clause per comma or semicolon, each ending
  `[verify: <tier> @ <evidence>]`. A clause only an out-of-band tier can settle is written
  that way on purpose, not dressed as automated.
- **Touch points**: every production file, registry consumers included, each marked
  `(modify)`, `(new)`, or `(delete)` with its purpose.
- **Out of scope**: adjacent work with where it lives; excluded instances with the benign
  claim.
- **Context**: why, with any linked source summarized. Never a reference to this session.

## Step 5 — Lint

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/scripts/lint_draft.py docs/tickets/<slug>.md --repo "${CLAUDE_PROJECT_DIR}"
```

Fix every ERROR. For each WARN, fix it or confirm the flagged text is concrete. Re-run
until it exits 0.

## Step 6 — Adversarial ticket review

Launch `ticket-adversary`. **The delegation prompt contains only the absolute path to the
draft.** Not the request, not what you learned in Step 2, not where you expect trouble —
it reads the tickets the way `plan-work` will, cold, and anything you add is context
`plan-work` will not have.

Fix every BLOCKER and MAJOR in the ticket text. A finding that misread a ticket means the
ticket is ambiguous: fix the text, never explain it to the reviewer. Re-lint, re-review.
Stop at no BLOCKERs or three rounds, whichever is first; revert-not-iterate applies. At
the cap, bring the remaining findings to Rob.

Append each round's output to the draft under `<!-- review round N -->`. That section
never reaches Jira.

## Step 7 — Present for approval

In chat, one table — ID, type, summary, handoff, AC clauses, touch points, blocked by —
followed by:

- clauses that need out-of-band verification, called out separately
- any sequenced split from Step 3, and every DECISION from the review
- assumptions stated in place of questions

Then stop and wait. Approval is an explicit "approved", "create them", or equivalent; a
clarifying question is not approval.

## Step 8 — Create

Look up the project's issue types and link types via the Atlassian MCP first; never guess
a name or ID.

1. Epics first, then the rest in draft order.
2. Summary; description with every `##` section except Open questions and review output;
   parent; labels, including the `Handoff:` label.
3. For each Blocked-by entry, a link of the blocking type with the blocker as outward.
4. After each creation, write the key into its `Jira:` line and replace its local ID with
   the key everywhere in the draft before creating the next ticket.
5. Read each ticket back. Headings, AC count, and every `[verify: …]` tag and inline code
   span must match the draft; if the conversion lost any, update and read back again.

For `<TICKET-N ...>` arguments: fetch them into a draft with `Jira:` filled, run Steps 2–7,
and update instead of create. A ticket that must split keeps its key for the ACs it
retains; say which new key holds the rest.

## Step 9 — Report

Each key with summary and URL, the handoff labels in order, and the `plan-work` command for
the first handoff.
