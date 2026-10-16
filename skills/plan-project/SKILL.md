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
`{{brief_file}}`: no branch and no commit until then, and no push at all.

## Step 1 — Read the configuration

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `brief_file`, `project_size`, `lifecycle_model`, `roles`,
`results_file`, and `results_read_command`.

Stop, and say why in one line, when:

- **`{{brief_file}}` is `none`** — absent or set so. Name the key: the brief has nowhere to
  live, and a path this skill chose would be a guess about the project's layout.
- **`.claude/state/current-plan.json` exists without `"paused": true`.** A delivery run is
  in flight, and the branch guard moves HEAD back to its branch after any command that
  leaves it, which would undo Step 5's switch.
- **The checked-out branch is not `{{parent_branch_default}}`.** Step 3 checks the build
  the brief's branch is cut from, so it runs there; say which branch to switch to.
- **`git check-ignore -v {{brief_file}}` matches.** The brief is committed in Step 5, and an
  ignored path fails there, after the sponsor has decided; name the rule it printed.
- **`{{brief_file}}` exists and its `## Decision` reads `Approved` or `Rejected`.** The
  brief is decided; name the decision rather than revise it.

An existing `{{brief_file}}` whose decision is `Pending`, or that has no `## Decision`
section yet, is the draft: read it, and revise
it in Step 2 rather than writing over it unread.

## Step 2 — Write the brief

Write `{{brief_file}}` from this template, every section in this order:

```markdown
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
for before writing anything. A value neither supplies is a proposal: write
it, mark it `(proposed)`, and list it at Step 4 for the sponsor to confirm or change — a
stated assumption rather than a blocking question. Never leave a placeholder in the file.

Then check the file against each rule, and fix what fails before going on:

1. **Every success measure has a number.** A line under `## Success measures` whose target
   — the text between `:` and ` by ` — holds no digit is rejected: rewrite it with a numeric
   target, or remove it. The target runs from the first `:` to the last ` by `, so a digit
   in the date does not count, and a line not in `<Measure>: <target> by <date>` form is
   rejected too. "Faster checkout by 2027-03-01" is not a measure; "Checkout time: under
   2 s at p95 by 2027-03-01" is.
2. **`## Risks` passes criterion 3** of `${CLAUDE_PLUGIN_ROOT}/gates/planning-exit.md`, the
   rule book's top five, each `Owner` a person or a role from `roles`.
3. **`## Lifecycle`** names `{{lifecycle_model}}` and an iteration length in weeks. Under
   `waterfall` or `continuous`, which have no iterations, it is the cadence at which the
   brief is reviewed again.
4. **`## Estimate`** is a range in weeks, low before high, never a single number or date.
5. **With `{{project_size}}` `small`, the file is at most 60 lines** — the rule book lets a
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

Stop, too, when `brief/<slug>` or `origin/brief/<slug>` already exists — `<slug>` the
project name in lowercase kebab-case — and ask rather than reuse it.

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
  stays `Pending` in the working tree, and a later run presents it again.

A clarifying question is not an answer. Only the sponsor's answer counts; one relayed by
the person running the session is printed as relayed.

## Step 5 — Record the decision and commit

Replace the `Pending — <sponsor>.` line under `## Decision` with the decision, the
sponsor, and today's date from `date +%F`:

```markdown
Approved by <sponsor> on <YYYY-MM-DD>.
```

The record names who gave the answer, not only who holds the role. Compare
`gh api user --jq .login` with `roles.sponsor`: when they differ, or `gh` cannot say, the
answer was relayed, and the line adds `, relayed by <login or git user.name>` before the
period — whatever the person running the session said about where it came from.

An approval confirms every `(proposed)` value as written, so remove those marks with it.
`Rejected` takes the same form, with the reason in one more line. A rejected brief is
committed too: it is the record that the project was stopped at the gate.

Run `git fetch` first; if `origin/{{parent_branch_default}}` moved since Step 3, re-run
Step 3 and present again before recording anything. Then cut the branch, with the `<slug>`
Step 3 checked, and commit the brief alone:

```bash
git switch -c brief/<slug> origin/{{parent_branch_default}}
git add {{brief_file}}
git commit -m "Record the project brief and the sponsor's decision" -- {{brief_file}}
```

Do not push: report the branch, the commit, and the decision, and leave publishing it to the
person running the session. An approved brief reaches `{{parent_branch_default}}`, where
`write-tickets` reads it, only when that branch is merged by an ordinary pull request:
`ship-pr` needs a ticket, and the brief precedes every ticket.
