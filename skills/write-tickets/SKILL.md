---
name: write-tickets
description: Turn a feature request, spec, bug report, or approved feature design into Jira epics, stories, tasks, and bugs that plan-work can plan without proposing a split, writing a Deviation, or leaving an AC clause unphased. Drafts to a file, lints it, has ticket-adversary review it cold, and creates the tickets only after approval.
argument-hint: <what to write tickets for> | <design path> | <TICKET-N ...> to rewrite existing ones
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task
---

Write tickets for: $ARGUMENTS

This skill produces tickets that the next stage can plan as written. Read
`${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/rubric.md` and
`${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md` before drafting.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json` first: `{{ticket_prefix}}`,
`{{jira_project}}`, `{{registry_file}}`, `{{source_roots}}`, `{{verification_tiers}}`,
`{{plan_rules_file}}`, `{{build_command}}`, `{{parent_branch_default}}`, `{{brief_file}}`,
`{{disciplines}}`, `{{design_dir}}`, and `{{roles.*}}` all come from it. Read
`${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly: tickets written
against invented tiers and roots fail at `plan-work` for reasons nobody can see.

No ticket is created, edited, or transitioned before Step 7's approval; until then it
writes only the draft and the input files of the checks it runs.

## Step 1 — Settle the decisions

State the requested outcome in one sentence. Then list every choice that changes behavior
and is not yet made: data format, error shape, UI copy, limits, library, which layer owns
the logic. With a design, read it first, as Step 2 says, and list only the choices it leaves
open; a choice Rob wants made differently from the design sends the design back to
`design-feature`. Ask Rob all of them in one message and wait.

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
- **the brief's goals**, which `Goal:` lines draw on: the `## Goals` of `{{brief_file}}`,
  read only when its `## Decision` reads `Approved`; otherwise say in one line why none were
  read — `none`, no file at the path, no `## Decision` or one other than `Approved`, or no
  goals. With `{{brief_file}}` set, stop unless it is `Approved` with a goal naming an
  outcome, never "none", "TBD", or "N/A": a goalless one goes back to the sponsor; a
  `Rejected` one stopped the project; a missing, `Pending`, or undecided one goes to
  `{{roles.sponsor}}` through `plan-project`, which records the decision.
- **the design** the request names: at `{{design_dir}}` `none`, stop and name the key. Write
  its path to a file per **Untrusted text**; stop if `git fetch` fails, or if `python3
  "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" design-read --ref
  "origin/{{parent_branch_default}}" --config "<project root>/.claude/project.json" < "<file>"`,
  the root written as its absolute path, exits non-zero. Read the design only
  from what it prints, and the Epic's `- Design:` path only from that file. Its `Work plan`
  is then the slice: a Step 3 split, an added ticket, or a review finding that would change a
  handoff's tickets stops the run and sends the design back to `design-feature` for rework.

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
   `plan-work`'s handoff limit. With a design, each `Work plan` handoff is one group, named
   as the handoff, holding its tickets in its order.

## Step 4 — Draft

Write `docs/tickets/<slug>.md` (gitignored) in the templates' format, blockers before
dependents; revise a draft already there if it is this request's, or ask. `<slug>` is
what this prints for the request, given as a file per **Untrusted text** in
`gates/project-config.md`; on an `INVALID:` line, ask for the request in Latin letters:

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
  "{{ticket_prefix}}"` and the issue is an Epic. Fetch it and each not-Done child into the
  draft as rewrite mode does, stopping on one no design ticket's summary matches, or on a
  design ticket a Done child matches, back to `design-feature`; draft the rest as new under
  it. Otherwise draft a new Epic from the design's Goals, Success measures, NFR thresholds, and
  Non-goals. Either Epic carries templates.md's one `- Design:` line; fetched tickets join here.

## Step 5 — Lint

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/scripts/lint_draft.py docs/tickets/<slug>.md --repo "${CLAUDE_PROJECT_DIR}"
```

Fix every ERROR, and fix each WARN or confirm its text is concrete; re-run until exit 0.
With a design, stop, naming the handoff, when a group's tickets differ from the handoff's
list in the design in count, summary, or order.
Exit 2, for an unreadable draft or project.json, bad `disciplines`, or bad `--repo`, stops.

## Step 6 — Adversarial ticket review

Launch `ticket-adversary`. **The delegation prompt contains only the absolute path to the
draft.** Not the request, not what you learned in Step 2, not where you expect trouble —
it reads the tickets the way `plan-work` will, cold, and anything you add is context
`plan-work` will not have.

Fix every BLOCKER and MAJOR in the ticket text. A finding that misread a ticket means the
ticket is ambiguous: fix the text, never explain it to the reviewer. Re-lint, re-review.
Stop at no BLOCKERs or three rounds, whichever is first; revert-not-iterate applies. At
the cap, bring the remaining findings to Rob.

Append each round's output under `<!-- review round N -->` in the draft, never sent to Jira.

## Step 7 — Present for approval

In chat, one table — ID, type, summary, priority, severity, handoff, AC clauses, touch
points, blocked by — followed by:

- clauses that need out-of-band verification, called out separately
- each ticket Step 4 removed for serving no goal of the brief
- any sequenced split from Step 3, and every DECISION from the review
- assumptions stated in place of questions

Ask `{{roles.qa}}` to confirm the ACs of every `Priority: Must` ticket are testable, and fix
any QA finds untestable. Then stop and wait for `{{roles.product_owner}}`, the gate's one
accountable role in RACI terms, whose approval counts only once QA has confirmed; one person
holding both roles gives both in one answer. Print both per `gates/project-config.md`. Any
edit after Step 6, whoever asks for it, re-runs Step 5 and one Step 6 round outside its
three-round count; a BLOCKER from it goes to `{{roles.product_owner}}`, and an edit to a
`Must` ticket's ACs goes back to QA, as a new commit dismisses a stale approval. Approval is
an explicit "approved", "create them", or equivalent; a clarifying question is not approval.

## Step 8 — Create

Look up issue and link types via the Atlassian MCP first; never guess a name or ID.

1. Epics first, then the rest in draft order.
2. Summary, parent, and labels: every `Labels:` value, the `Handoff:` label, for a
   non-empty `Priority:`, `moscow-<priority>` in lowercase — `Won't` is `moscow-wont` —
   and for a Bug, `severity-<severity>` in lowercase.
3. Description: `Goal: <sentence>` first when the header has one, then every `##` section
   except Open questions, Change impact, and review output, with each `[verify: …]` and
   `[children: …]` tag inside a code span, which the connector's read conversion keeps.
4. For each Blocked-by entry, a link of the blocking type with the blocker as outward.
5. After each creation, write the key into its `Jira:` line and replace its local ID with
   the key everywhere in the draft — as a whole ID, never the `S1` in `S10` — before
   creating the next ticket.
6. Read each ticket back with `jira_get_issue`, which returns Markdown. Check it carries
   exactly the labels item 2 names, save its description verbatim to
   `docs/tickets/<slug>.<key>.md`, and run:

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

For `<TICKET-N ...>` arguments and Step 4's fetched tickets, fetch each into a draft with
its key as the header ID and on its `Baseline:` and `Jira:` lines, so no local ID stands for
an issue that already exists, mapping:

- its `moscow-*` label to `Priority:` — `moscow-wont` as `Won't`, the rest title-cased; no
  such label, or more than one, leaves `Priority:` empty for Step 1 to settle
- on a Bug, its `severity-*` label to `Severity:`, title-cased; no such label, or more
  than one, leaves `Severity:` empty for Step 1 to settle; on any other type, none
- every other label but the handoff label to `Labels:` — never a `moscow-*` or
  `severity-*` label, which only the two headers above carry
- a leading `Goal:` description line to the `Goal:` header
- a code span holding a whole `[verify: … @ …]` or `[children: …]` tag, or the
  `\verify: …\` an older write left, to the bare tag

Run Steps 2–7 for `<TICKET-N ...>` arguments. Each ticket whose `Baseline:` is filled is
updated instead of created, its labels set to exactly item 2's, which drops a replaced
handoff label, the one label the mapping above does not carry. Each rewritten ticket carries
`## Change impact` (rubric R15). After item 7, when item 5 has replaced every local ID, post
each note once with `jira_add_comment`: a first line `Change impact`, then the section's
lines, tags in code spans as in item 3. The comment ID it returns confirms the post; a post
that returns none is never retried, since it may have landed. Any stop after the first
update — item 6's, a failed post, any other — brings Rob every note not yet confirmed. A
ticket that must split keeps its key for the ACs it retains; say which new key holds the rest.

## Step 9 — Report

Keys with summaries and URLs, handoff labels in order, the first handoff's `plan-work` call.
