---
name: review-tickets
description: Review an epic and its children, or named tickets, against the write-tickets rubric — lint, then a cold ticket-adversary review — and report every failed rule per ticket with the write-tickets command that would fix them. Changes nothing in Jira or the repository.
argument-hint: <EPIC-KEY> | <KEY ...>
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Task, mcp__atlassian__jira_get_issue, mcp__atlassian__jira_search
---

Review the tickets: $ARGUMENTS

This skill is the check half of a check-and-fix pair, as `ruff check` is to `ruff check
--fix`: it reports, and `write-tickets` fixes. **It changes nothing.** Of the Atlassian
tools it calls only `jira_get_issue` and `jira_search`, never `jira_update_issue`,
`jira_add_comment`, `jira_transition_issue`, `jira_create_issue_link`,
`jira_remove_issue_link`, or any other that writes; the agents it dispatches follow
`gates/read-only-agent.md`. In the repository it never edits, stages, commits, stashes,
switches, or creates a branch. It writes two files, each outside the work tree, so
`git status` never shows them, and each removed once read: its input file, in the
directory Step 2 names, and its draft, in `<dir>`, the directory
`git rev-parse --path-format=absolute --git-path review-tickets` prints.

## Step 1 — Read the configuration and the rubric

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `design_dir`, `adr_dir`, `brief_file`, `disciplines`, `registry_file`,
`plan_rules_file`, and `pr_review_limit_lines`. None of them stops the review: an unset key
is announced, and the checks that read it judge without it.

Read `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/rubric.md` and
`${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md` in full. The rubric
is the one source of every rule ID and rule this report names; this file restates none.

## Step 2 — Resolve the arguments

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

Every `jira_get_issue` call names its fields, since the defaults leave out the parent
and the links: `fields` is `summary,issuetype,status,labels,parent,issuelinks,description`.

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
first, then the rest in the order Step 2 resolved them. Each is converted from what
`jira_get_issue` returns, as `write-tickets` converts a fetched ticket:

- the header ID and `Jira:` are the key; `Baseline:` stays empty, since a review rewrites
  nothing and a filled `Baseline:` marks a rewrite
- `Type:` is the issue type; `Parent:` the parent's key, on a ticket that has one;
  `Blocked by:` the key of each issue linked as blocking it, or `None`
- its one `moscow-*` label goes to `Priority:`, title-cased, `moscow-wont` as `Won't`; on
  a Bug, its one `severity-*` label to `Severity:`, title-cased. None, or more than one,
  leaves the header empty
- `Handoff:` stays empty: Jira does not mark which label is a ticket's handoff, so the
  draft names none rather than guess, and Step 8 reports it unknown
- every other label, `enabling` included, goes to `Labels:`, never a `moscow-*` or
  `severity-*` label, which only the two headers above carry
- a leading `Goal:` description line goes to the `Goal:` header
- each `##` section of the description, as written; a code span holding a whole
  `[verify: … @ …]` or `[children: …]` tag, or a `\verify: …\` an older write left,
  becomes the bare tag

Copy every line as Jira returned it. A section the ticket lacks stays absent: the lint
reports it, and filling it in would review a ticket that does not exist.

## Step 4 — Lint

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/scripts/lint_draft.py" "<dir>/draft.md" --repo "<absolute project root>"
```

Keep every `ERROR` and `WARN` line, except those below, which describe the draft rather
than the ticket; Step 8 reports them as unknown instead:

- `[R2] missing Handoff label`, which every Story, Task, and Bug draws, since `Handoff:`
  is empty by design
- in key mode, an `E2` line naming an unknown child that `jira_search` for `parent = <Epic
  key>` returns: the child exists, and only the review left it out
- an `R3` line on a ticket whose `Blocked by:` names a key not in the draft: that blocker
  may create the file, and the linter sees only the draft's tickets

Exit 0 and 1 both go on; exit 2 stops the run, printing its `UNPARSEABLE` line.

## Step 5 — Review it cold

Launch `ticket-adversary` once. **The delegation contains only the absolute path to
`<dir>/draft.md`**: no lint output, no request, no hint. It reads the tickets as `plan-work`
will. There is no second round, since nothing is fixed between rounds.

## Step 6 — The design

The design section reads `Design — not checked: <reason>`, one line, and is neither a pass
nor a fail. In key mode the reason is `given ticket keys, not an Epic`; in Epic mode, `the
design check is not part of this skill yet`.

## Step 7 — Clean up

Remove `<dir>/draft.md` by that path, then the empty `<dir>` with `rmdir`. Do the same
before any stop once the draft exists.

## Step 8 — Report

One section per ticket under review, in draft order: `## <KEY> — <summary> — PASS` or
`— FAIL`. Under it, one line per finding:

```
- <rule ID> — <the ticket text that fails it, quoted> — <the fix, from the finding> (lint | review <severity>)
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
  `Handoff:` being empty, or in key mode on a child being absent from the draft.

An `Across the draft` finding naming no ticket, and in key mode with no Epic among the keys
an Epic-level finding, goes in a `## Across the draft` section after the tickets, rated as
the review rated it, counted against no ticket. That section ends with one line saying the
linter's handoff-size check did not run, since no `Handoff:` is filled.

A ticket **fails** on any lint `ERROR` or review BLOCKER or MAJOR; a `WARN` or MINOR is
reported and fails nothing. A ticket with no finding reads `- none`. A ticket whose status
is past Jira's To Do category is past planning, which the rubric judges readiness for, and
its code has moved on since: its findings are listed, but its heading reads `— <status>,
not judged` in place of PASS or FAIL, and it is neither counted nor handed to
`write-tickets`.

Then the design section, Step 6's. The report ends with the summary, in this order:

```
| Ticket | Lint errors | Lint warnings | Review BLOCKER | Review MAJOR | Result |
```

one row per ticket, `not judged` in its Result past To Do, then
`PASS: <n>  FAIL: <n>  NOT JUDGED: <n>`, then the last line:
`NEXT: /delivery-kit:write-tickets <each failing key, in draft order>`, or, when none
fails, `NEXT: none — every ticket passes`.
