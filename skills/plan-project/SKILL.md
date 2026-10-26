---
name: plan-project
description: Write the rule book's Phase 1 project brief — problem, users, goals, non-goals, numeric success measures, constraints, five owned risks, lifecycle, and an estimate range — confirm the build and CI pass, stop for the sponsor's decision, then record it and commit the brief on its own branch.
argument-hint: <what the project is for>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Write the project brief for: $ARGUMENTS

This skill is the rule book's Phase 1 in its order: steps 1–5 write the brief, step 6's
repository and CI are confirmed, and step 7 reviews it with the sponsor and records the
decision. No file is created, edited, or staged before the sponsor answers except
`{{brief_file}}` and the input files **Untrusted text** in `gates/project-config.md` places
under the git directory: no branch and no commit until then, and no push at all.

## Step 1 — Read the configuration

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `brief_file`, `project_size`, `lifecycle_model`, `roles`,
`results_file`, and `results_read_command`.

Stop, and say why in one line, when:

- **`{{brief_file}}` is `none`** — absent or set so. Name the key: the brief has nowhere to
  live, and a path this skill chose would be a guess about the project's layout. Stop too,
  naming it, when `python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" brief-read
  --path --config "<absolute project root>/.claude/project.json"` prints `INVALID:`: every
  reader of the brief checks its path that way.
- **`.claude/state/current-plan.json` exists without `"paused": true`.** A delivery run is
  in flight, and the branch guard moves HEAD back to its branch after any command that
  leaves it, which would undo Step 5's switch.
- **The checked-out branch is not `{{parent_branch_default}}`.** Step 3 checks the build the
  brief's branch is cut from, so it runs there; say which branch to switch to.
- **`{{brief_file}}` is ignored**, as **Ignored paths** in `gates/project-config.md`
  decides. The brief is committed in Step 5, and an ignored path fails there, after the
  sponsor has decided; name the rule.
- **`{{brief_file}}` exists with front matter whose `status` is not `proposed`, or, written
  before briefs carried front matter, with a `## Decision` that reads other than
  `Pending`.** It is decided, or in a state no step writes; name it rather than revise it,
  and say a decided one gains its `status` by hand.

**An interrupted Step 5 comes first, after the first two stops.** When
`git rev-parse --path-format=absolute --git-path plan-project` names a directory that
exists, Step 5 started and did not finish — the way `.git/rebase-merge` tells git a rebase
is in progress. First, when `git show brief/<slug>:{{brief_file}}` already holds the
`decision` line, the commit landed and only cleanup was lost: remove the directory, report
that commit, and offer no abort. Otherwise continue, keeping the recorded decision: switch
to `brief/<slug>`, or, if it is absent, cut it from the commit in `base` — from
`origin/{{parent_branch_default}}` when a directory written before `base` existed has none —
make the `## Decision` line match `decision`, `status` match `status` — `accepted` or
`rejected` as `decision` opens, when a directory written before `status` existed has none —
and `date` match the date `decision` carries, and commit as Step 5 does. On an explicit
abort instead, unstage the brief with `git restore --staged {{brief_file}}`, restore it from
`presented.md`, switch to `{{parent_branch_default}}`, delete `brief/<slug>` if it has no
commits of its own, and remove the directory — leaving index and tree as before Step 5, as
`git rebase --abort` does. No other stop applies while it exists.

Any other existing `{{brief_file}}` is the draft: read it, add the template's front matter
where it is missing, and revise it in Step 2 rather than writing over it unread.

## Step 2 — Write the brief

Write `{{brief_file}}` from this template, every section in this order:

```markdown
---
status: proposed
date: <YYYY-MM-DD, from date +%F>
decision-makers: <sponsor>
---

# <Project name> — project brief

## Problem
<What is wrong today, for whom, and why it matters now.>

## Users
<Who uses the result, and who is affected by it.>

## Goals
- <An outcome, one line each.>

## Non-goals
- <What this project will not do, one line each.>

## Success measures
- <Measure>: <number and unit> by <date or milestone>

## Constraints
- Deadline: <date>
- Budget: <amount, or none>
- Team size: <people>
- Platforms: <required platforms>
- Compliance: <obligations, or none>

## Risks
| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| <risk> | low/medium/high | <what it costs if it happens> | <mitigation or fallback> | <person or role> |

## Lifecycle
{{lifecycle_model}}, in iterations of <N> weeks.

## Estimate
<N>–<M> weeks.

## Decision
Pending — <sponsor>.
```

`<sponsor>` here and in Step 5 is the handle `roles.sponsor` holds. With no sponsor in
`roles` the sponsor is the person running the session, per `gates/project-config.md`: use
their git `user.name`, or ask for a name when it is unset — a name, never the word "you".

Fill it from $ARGUMENTS and the repository; with $ARGUMENTS empty, ask what the project is
for before writing anything. A value neither supplies is a proposal: write it, mark it
`(proposed)`, and list it at Step 4 for the sponsor to confirm or change — a
stated assumption rather than a blocking question. Never leave a placeholder in the file.

Then check the file against each rule, and fix what fails before going on:

1. **`## Goals` names at least one outcome.** An empty section, or an item reading "none",
   "TBD", or "N/A", fails: `write-tickets` traces every goal line to one of these.
2. **Every success measure has a number.** A line under `## Success measures` whose target
   — the text between `:` and ` by ` — holds no quantity, a number with a unit, percent, or
   comparator, is rejected: rewrite it with a numeric target, or remove it. A digit inside a
   name such as `p95` is not a quantity. The target runs from the first `:` to the last ` by `, so a digit
   in the date does not count, and a line not in `<Measure>: <target> by <date>` form is
   rejected too. "Faster checkout by 2027-03-01" is not a measure; "Checkout time: under
   2 s at p95 by 2027-03-01" is.
3. **`## Risks` passes criterion 3** of `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md`, the
   rule book's top five, each `Owner` a person or a role from `roles`.
4. **`## Lifecycle`** names `{{lifecycle_model}}` and an iteration length in weeks. Under
   `waterfall` or `continuous`, which have no iterations, it is the delivery cadence: how
   often finished work is reviewed and released.
5. **`## Estimate`** is a range in weeks, low before high, never a single number or date.
6. **With `{{project_size}}` `small`, the file is at most 60 lines** — the rule book lets a
   small project's brief fit one page. Count with `wc -l < {{brief_file}}`; over 60, cut
   prose, never a section or a risk row. `medium` and `large` have no line cap.

## Step 3 — Confirm the repository and CI

This is the rule book's step 6, checked rather than performed. Criterion 4 of
`${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md` is the one definition of what passes: its
preconditions, `{{build_command}}`, and the two `gh run list` commands, starting with
`gh run list --branch {{parent_branch_default}} --limit 1 --json conclusion`. Run them as
it states, and **stop unless each passes**, naming what was reported; a failed fetch or a
`gh` error is named as that. When `{{results_file}}` is not `none`, the build's verdict is
read from it with `{{results_read_command}}` rather than from the console.

Stop, too, when `brief/<slug>` or `origin/brief/<slug>` already exists, and ask rather than
reuse it. `<slug>` is what this prints for the project name, handed over as a file per
**Untrusted text** in `gates/project-config.md`; an `INVALID:` line, as for a name with no
Latin letter or digit, asks for the name in Latin letters:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" slug < "<name file>"
```

A failure here is not repaired by this skill: setting up or fixing the build and pipeline
is the project's step 6 work. The brief stays in place, and a re-run presents it once both
pass.

## Step 4 — Stop for the sponsor

Check every criterion in `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md` against the brief
and Step 3; fix a failing criterion 2 or 3 in the brief before going on. Then present to
`{{roles.sponsor}}`, printed per `gates/project-config.md`:

- the brief's path and its line count
- every `(proposed)` value, one line each
- each exit criterion and how it stands, with "Brief approved by sponsor" open

Then stop and wait. The answer is one of Stage-Gate's four:

- **Approve** (Go) or **reject** (Kill) — a decision, and a final one. Go to Step 5.
- **Rework** (Recycle) — changes asked for, which is not a decision. Revise the brief,
  re-run Step 2's checks, then `git fetch`, the slug, and its branch check from Step 3, and
  present again; the rest of Step 3 re-runs only if `origin/{{parent_branch_default}}`
  moved. Revision happens here, never after a rejection.
- **Hold** — the sponsor defers the decision. Record nothing and commit nothing: the brief
  stays `Pending` and `proposed` in the working tree, and a later run presents it again.

A clarifying question is not an answer. Only the sponsor's answer counts; one relayed by
the person running the session is printed as relayed.

## Step 5 — Record the decision and commit

Run `git fetch` first; if `origin/{{parent_branch_default}}` moved since Step 3, or
`origin/brief/<slug>` now exists, re-run Step 3 and present again before recording
anything.

Before touching the brief, write the operation's state where git keeps its own, in the
directory `git rev-parse --path-format=absolute --git-path plan-project` names:
`presented.md`, a copy of the brief as Step 4 presented it; `slug`; `base`, the commit
`origin/{{parent_branch_default}}` names after that fetch; `decision`, the line below; and
`status`, `accepted` or `rejected`. Then set the front matter's `status` to it and `date` to
today's from `date +%F`, as MADR records a decision, and replace the `Pending — <sponsor>.`
line under `## Decision` with the decision, the sponsor, and that date:

```markdown
Approved by <sponsor> on <YYYY-MM-DD>.
```

The record names who gave the answer, not only who holds the role. It was relayed when
the person running the session says so, per `gates/project-config.md`, or when
`roles.sponsor` is set, as a GitHub login, and `gh api user --jq .login` names someone
else or cannot say. A relayed answer adds `, relayed by <that login, or git user.name>`
before the period. With no sponsor in `roles`, only the first test applies.

An approval confirms every `(proposed)` value as written, so remove those marks with it.
`Rejected` takes the same form, with the reason in one more line. A rejected brief is
committed too: it is the record that the project was stopped at the gate.

Then cut the branch, with the `<slug>` Step 3 checked, and commit the brief alone:

```bash
git switch -c brief/<slug> <base>
git add {{brief_file}}
git commit -m "Record the project brief and the sponsor's decision" -- {{brief_file}}
```

Remove the state directory once the commit succeeds. When the commit fails — a hook
rejects it, say — fix what it names and commit again; the sponsor's answer stands. If that
cannot be done in this run, stop with the directory in place and say so: the next run
continues or aborts it, as `git rebase --continue` and `--abort` do.

Do not push: report the branch, the commit, and the decision, and leave publishing it to the
person running the session. An approved brief reaches `{{parent_branch_default}}`, where
`write-tickets` reads it, only when that branch is merged by an ordinary pull request:
`ship-pr` needs a ticket, and the brief precedes every ticket.
