---
name: review-tickets
description: Review an epic and its children, or named tickets, against the write-tickets rubric — lint, then a cold ticket-adversary review — and report every failed rule per ticket with the write-tickets command that would fix them, and the Epic's recorded design through feature-design-adversary. Makes no Jira write of its own and changes nothing in the repository; its scratch files and a temporary worktree live under the git directory and are removed.
argument-hint: <EPIC-KEY> | <KEY ...>
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Task, mcp__atlassian__jira_get_issue, mcp__atlassian__jira_search
---

Review the tickets: $ARGUMENTS

This skill is the check half of a check-and-fix pair, as `ruff check` is to `ruff check
--fix`: it reports, and `write-tickets` fixes. **It changes nothing itself.** Of the
Atlassian tools it calls only `jira_get_issue` and `jira_search`, never
`jira_update_issue`, `jira_add_comment`, `jira_transition_issue`, `jira_create_issue_link`,
`jira_remove_issue_link`, or any other that writes. The agents it dispatches follow
`gates/read-only-agent.md`, which covers the repository only; they hold the Atlassian
tools, writes included, and this skill cannot narrow them. In the repository it never
edits, stages, commits, stashes, switches, or creates a branch. Everything it writes is
outside the work tree, so `git status` never shows it, and is removed once read: its input
files, in the directory Step 2 names; its draft, in `<dir>`, the directory
`git rev-parse --path-format=absolute --git-path review-tickets` prints; and, for a design,
a temporary worktree inside the git directory. The design's fetch also overwrites
`FETCH_HEAD`, which is left as git leaves it.

## Step 1 — Read the configuration and the rubric

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `design_dir`, `adr_dir`, `brief_file`, `disciplines`, `registry_file`,
`plan_rules_file`, and `pr_review_limit_lines`. An unset one stops nothing: it is
announced, and the checks that read it judge without it. A `disciplines` naming an unknown
discipline stops the review at Step 4, where the linter refuses it.

Read `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/rubric.md` and
`${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md` in full. The rubric
is the one source of every rule ID and rule this report names; this file restates none.

## Step 2 — Resolve the arguments

One review runs per checkout, as git takes `index.lock`: create `<dir>` with `mkdir`,
never `mkdir -p`, so the one command both checks and claims it. When it fails because
`<dir>` exists, stop, naming it: another review is running there, or one was killed, and
once none is running the person removes `<dir>` and runs the review again. Every stop
after the `mkdir` succeeds removes `<dir>`, as Step 7 says.

With `$ARGUMENTS` empty, ask for an Epic key or ticket keys, and stop. Otherwise write it
to a file per **Untrusted text** in `gates/project-config.md`, in the directory
`git rev-parse --path-format=absolute --git-path review-tickets-input` prints, run this,
and remove the file and, once empty, its directory:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" ticket-keys --prefix "{{ticket_prefix}}" < "<arguments file>"
```

It prints each distinct key under `{{ticket_prefix}}` once, sorted. Take them in the
order `$ARGUMENTS` first names them, and name, in one line, each word of `$ARGUMENTS` that
became no key, such as a key under another prefix or in lowercase, as skipped. With none
printed, say so, ask for keys, and stop.

Every `jira_get_issue` call names the `fields` templates.md's fetched ticket lists, since
the defaults leave out the parent and the links.

- **Epic mode** — exactly one key, and `jira_get_issue` returns it as an Epic. Its
  children are every issue `jira_search` returns for `parent = <KEY> ORDER BY created ASC`,
  all pages, whatever their status, each then fetched with `jira_get_issue`. The review
  covers the Epic and each child.
- **Key mode** — anything else. The review covers exactly the keys printed, an Epic among
  them included, and nothing more: a ticket's epic and blockers are context
  `ticket-adversary` reads from Jira itself, not tickets under review.

Print the resolved set, key, type, and summary, before going on. A fetch that fails stops
the run, naming the key and quoting the error.

## Step 3 — Fetch into a draft

Write every ticket under review to `<dir>/draft.md` in templates.md's format, the Epic
first, then the rest in the order Step 2 resolved them, each drafted as templates.md's
fetched ticket, except:

- the header ID and `Jira:` are the key; `Baseline:` stays empty, since a review rewrites
  nothing and a filled `Baseline:` marks a rewrite
- `Handoff:` stays empty: Jira does not mark which label is a ticket's handoff, so the
  draft names none rather than guess, and Step 8 reports it unknown. Every label but a
  `moscow-*` or `severity-*` one, `enabling` included, goes to `Labels:`

Copy every other line as Jira returned it. A section the ticket lacks stays absent: the lint
reports it, and filling it in would review a ticket that does not exist.

## Step 4 — Lint

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/scripts/lint_draft.py" "<dir>/draft.md" --repo "<absolute project root>"
```

Keep every `ERROR` and `WARN` line, except those below, which describe the draft rather
than the ticket; Step 8 reports them as unknown instead:

- `[R2] missing Handoff label`, since `Handoff:` is empty by design
- in key mode, an `E2` line naming an unknown child that `jira_search` for `parent = <Epic
  key>` returns: the child exists, and only the review left it out
- an `R3` `no Blocked-by ticket creates it` line on a ticket whose blockers, followed
  through the draft's `Blocked by:` lines, reach a key not in the draft, since the linter
  sees only the draft's tickets

Exit 0 and 1 both go on; exit 2 stops the run, printing its `UNPARSEABLE` line.

The linter's R14 sees a goal's presence, not what it serves; rubric R14 also ties each
goal to the approved brief. At `{{brief_file}}` `none`, say in one line that goals were
not traced to a brief. Otherwise run this; on `INVALID:`, print that line, without its
`NEXT:` line, as the reason goals were not traced, and go on. Relay a `DEPRECATED:` line
as it is:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" brief-read --config "<absolute project root>/.claude/project.json"
```

A brief whose `## Goals` names no outcome, only "none", "TBD", or "N/A", is the defect:
say so in one line as the reason goals were not traced. Otherwise each ticket's `Goal:`
header, and an Epic's `## Goal`, that restates none of the brief's goals is an `R14`
finding tagged `(brief)`, which fails its ticket, quoting the goal and naming the brief's
goals as the fix.

## Step 5 — Review it cold

Launch `ticket-adversary` once. **The delegation contains only the absolute path to
`<dir>/draft.md`**: no lint output, no request, no hint. It reads the tickets as `plan-work`
will. There is no second round, since nothing is fixed between rounds.

## Step 6 — The design

The design section opens `## Design`, in one of two forms. **Not checked** is the heading
`## Design — not checked: <reason>` and nothing under it, neither a pass nor a fail; the
first reason that applies, in this order, is the one given:

1. Key mode: `given ticket keys, not an Epic`.
2. `{{design_dir}}` unset or `none`: `design_dir is <unset | none>`.
3. The Epic's `## In scope` holds no `- Design:` line, templates.md's form: `the Epic
   names no design`; or more than one: `the Epic names <n> designs`.
4. A command below, up to the reviewer's launch, exits non-zero: its `INVALID:` line, or
   its error, quoted. A `NEXT:` line it prints is left out, since the report names
   `design-feature` only for a design finding.

Write the `- Design:` path, backticks dropped, to a file per **Untrusted text**, in Step
2's input directory, and remove it with that directory once `design-read` has run or a
command before it has failed. Fetch the parent into `FETCH_HEAD` alone, so no
remote-tracking ref moves and `git status` reports the same ahead or behind as before,
then ask `design-read` for the checked path at that commit:

```bash
git fetch --refmap= origin "{{parent_branch_default}}" && git rev-parse FETCH_HEAD
python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" design-read --path --ref "<the commit printed>" --config "<absolute project root>/.claude/project.json" < "<path file>"
```

`design-read` reads only an accepted design; the path it prints is the one reviewed. Check
that commit out as this skill's own base tree, so the reviewer reads the text `design-read`
judged, whatever the checkout holds, and keep the path it prints. `review-tickets` is its
owner, so the tree is never `design-feature`'s, and adding it first removes one a killed
run of this skill left:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-feature/scripts/design_check.py" base-tree add "<the commit printed>" --owner review-tickets --config "<absolute project root>/.claude/project.json"
```

Launch `feature-design-adversary`. **The delegation contains only
`<tree>/<prefix><checked path>`**, the design doc's absolute path in that tree, `<prefix>`
what `git rev-parse --show-prefix` prints run from the project root, empty when the
project is the repository's top level. Once it returns, and before any stop after the
`add`, run this; a failure here is one line after the four headings and before any
`NEXT:` line, never in place of the findings:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-feature/scripts/design_check.py" base-tree remove --owner review-tickets --config "<absolute project root>/.claude/project.json"
```

**Checked** is the heading `## Design — <checked path>`, then the reviewer's `BLOCKER`,
`MAJOR`, `MINOR`, and `UNVERIFIABLE` findings under those four headings, as it returned
them, `none` under an empty one, and nothing from the ticket findings. With at least one
BLOCKER or MAJOR, the section ends with `NEXT: /delivery-kit:design-feature <EPIC-KEY>`,
then each BLOCKER and MAJOR quoted verbatim, for its reopen's `## Revision history`. With
none, it prints no `design-feature` command.

## Step 7 — Clean up

Remove `<dir>/draft.md` by that path, once Step 3 has written it, then the empty `<dir>`
with `rmdir`. Do the same before any stop after Step 2 created `<dir>`.

## Step 8 — Report

One section per ticket under review, in draft order: `## <KEY> — <summary> — PASS` or
`— FAIL`. Under it, one line per finding:

```
- <rule ID> — <the ticket text that fails it, quoted> — <the fix, from the finding> (lint | brief | review <severity>)
```

- A lint line keeps the code it printed and its key. A `FORMAT` or `JIRA` line names no
  rubric rule: cite `templates.md` beside the code.
- A `ticket-adversary` finding is reported under the rubric ID it names, or, when it names
  none, the one rule from rubric.md whose text it fails. A finding on an Epic-level rule
  is reported under the Epic, whichever ticket it names; one under `Across the draft` goes
  under each ticket it names.
- A `DECISION` is listed under its ticket as a question, with no rule ID, and counts for
  nothing.
- Each line Step 4 set aside reads `- <code> — unknown: <why> — <the labels or the key>`
  and counts for nothing; so does a review finding that rests only on a ticket's
  `Handoff:` being empty, in key mode on a child being absent from the draft, or on overlap
  with the ticket's own Jira issue, the same key.

A `## Across the draft` section always follows the tickets. It holds, or `- none`, each
`Across the draft` finding naming no ticket, and in key mode with no Epic among the keys
each Epic-level finding, rated as the review rated it and counted against no ticket. It
ends with one line saying the linter's handoff-size check did not run, since no `Handoff:`
is filled.

A ticket **fails** on any lint `ERROR`, `(brief)` finding, or review BLOCKER or MAJOR; a `WARN` or MINOR is
reported and fails nothing. A ticket with no finding reads `- none`. A ticket past Jira's
To Do category has been planned, and its code has moved on since: its findings are listed,
but its heading reads `— <status>, not judged` in place of PASS or FAIL, and it is neither
counted nor handed to `write-tickets`. An Epic is the exception until Jira's Done category:
its rules check its children, some of which may not have started.

Then the design section, Step 6's. The report ends with the summary, in this order:

```
| Ticket | Lint errors | Lint warnings | Brief | Review BLOCKER | Review MAJOR | Result |
```

one row per ticket, `not judged` in its Result where its heading reads it, then
`PASS: <n>  FAIL: <n>  NOT JUDGED: <n>`, then the last line:
`NEXT: /delivery-kit:write-tickets <each failing key, in draft order>`, or, when none
fails, `NEXT: none — every ticket passes`.
