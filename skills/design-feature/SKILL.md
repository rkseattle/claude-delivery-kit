---
name: design-feature
description: Write the rule book's Phase 3 design for a whole feature or epic — survey, current state, options, components, ADRs, and a work plan — against the approved brief and the existing code, have feature-design-adversary review it cold, stop for QA, the product owner, and the tech lead, then record the decision and commit the design and its ADRs on their own branch.
argument-hint: <feature request> or <EPIC-KEY>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task, WebSearch, WebFetch, mcp__atlassian
---

Design the feature: $ARGUMENTS

This skill is the rule book's Phase 3 at feature scale, before any of the feature's tickets
are written. `${CLAUDE_PLUGIN_ROOT}/gates/design-exit.md` is its gate: it defines every
section, line form, ADR, approver, and `## Decision` line written here, and this file names
them rather than restating them. Read it in full before Step 2. No file is created, edited,
or staged before the tech lead answers except the design doc, its ADRs, and the input files
**Untrusted text** in `gates/project-config.md` places under the git directory: no branch
and no commit until then, and no push at all.

The flow is that of a Rust RFC or a KEP — draft, cold review, a decision by the accountable
approver, then the record committed with its status — with each costly choice a MADR
decision record, and the decision steps those of `plan-project` Steps 4 and 5. Where a KEP
or an RFC records approval as reviews on a pull request, this skill records it in
`## Decision` in the session and commits without pushing, as `gates/design-exit.md`
requires; the design's ordinary pull request is reviewed as code, after the decision.

## Step 1 — Read the configuration and check the prerequisites

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `design_dir`, `adr_dir`, `brief_file`, `disciplines`, `roles`,
`pr_review_limit_lines`, and `exceptions_log`.

Stop, and say why in one line, when:

- **`.claude/state/current-plan.json` exists without `"paused": true`.** A delivery run is
  in flight, and the branch guard moves HEAD back to its branch after any command that
  leaves it, which would undo Step 6's switch. A file that does not parse stops too.
- **This exits non-zero**, naming each key its `INVALID:` line names. `design_dir` unset is
  one: the design has nowhere to live.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-feature/scripts/design_check.py" dirs --config "${CLAUDE_PROJECT_DIR}/.claude/project.json"
  ```

  `ok`, a tab, and `adr_dir not configured` is no stop: say so in one line and go on. The
  gate fails such a design only when it holds a `- Costly to reverse:` line, and Step 3
  stops, naming `adr_dir`, before writing one.

**An interrupted Step 6 comes first, after those two stops.** When
`git rev-parse --path-format=absolute --git-path design-feature` names a directory that
exists, Step 6 started and did not finish — the way `.git/rebase-merge` tells git a rebase
is in progress — and its `slug` file names the design. First, when
`git show design/<slug>:{{design_dir}}/<slug>.md`
already holds the first line of `decision`, the commit landed and only cleanup was lost:
remove the directory, report that commit, and offer no abort. Otherwise continue, keeping
the recorded decision: switch to `design/<slug>` (or cut it from the commit in `base` if
absent), make every edit Step 6 makes from `decision` and `status`, and commit as Step 6
does, from `message`. On an explicit abort instead, unstage the design doc and its ADRs
with `git restore --staged`, restore each from `presented/`, switch to
`{{parent_branch_default}}`, delete `design/<slug>` if it has no commits of its own, and
remove the directory — leaving index and tree as before Step 6, as `git rebase --abort`
does. No other stop applies while it exists, and `$ARGUMENTS` is not needed.

Otherwise, run `git fetch origin`, and stop unless the checked-out branch is
`{{parent_branch_default}}` and `git rev-parse HEAD` equals
`git rev-parse origin/{{parent_branch_default}}`: the design describes that commit and
Step 6 cuts its branch from it. Say which branch to switch to, or that it must be brought
level with its `origin` ref. Then record that commit; Step 6 compares against it.

`$ARGUMENTS` is a feature request, or an Epic key: one when this, given `$ARGUMENTS` as a
file per **Untrusted text** in `gates/project-config.md`, prints it back rather than
`INVALID:`. With `$ARGUMENTS` empty, ask what the feature is.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" ticket-key --prefix "{{ticket_prefix}}" < "<arguments file>"
```

Given an Epic key, fetch the Epic and read its goal,
success measures, NFR lines, and children: **the design's title is the Epic's summary**,
as written. Given a request, first read the `# <title>` line of every design doc under
`{{design_dir}}`, whatever its decision: when one already designs this feature, its title
is the title, so a re-run finds its draft. A design committed only on a `design/*` branch
is caught by the branch stop below when its title comes out the same. Otherwise the title is a short noun phrase
naming the feature, stated in the first report.

`<slug>` is what this prints for the title, handed over as a file per **Untrusted text** in
`gates/project-config.md`; an `INVALID:` line stops the run, naming the title:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-feature/scripts/design_check.py" slug < "<title file>"
```

Then stop, and say why in one line, when:

- **`{{design_dir}}/<slug>.md` is ignored, or, with `adr_dir` set,
  `{{adr_dir}}/0000-<slug>.md` is**, as **Ignored paths** in `gates/project-config.md`
  decides. Both are committed in Step 6, and an ignored path fails there, after the tech
  lead has decided; name the key and the rule. Step 3 checks each ADR's own path again once
  it is named.
- **`{{brief_file}}` is set and the file is missing, or its `## Decision` line does not
  start with `Approved`.** The design restates the brief's goals, which an unapproved brief
  has not settled; name the decision it holds, and send a pending one to the sponsor through
  `plan-project`. With `brief_file` `none`, say in one line that there is no brief to frame
  the design against, and go on.
- **`{{design_dir}}/<slug>.md` exists with a `## Decision` that reads other than
  `Pending`.** The design is decided; name the decision rather than revise it.
- **`design/<slug>` or `origin/design/<slug>` exists.** Ask rather than reuse it.

An existing `{{design_dir}}/<slug>.md` whose decision is `Pending`, or that has no
`## Decision` section yet, is the draft: read it and its ADRs, and revise them in place in
Steps 2 and 3 rather than writing over them unread.

## Step 2 — Frame the feature and survey it

Frame the feature from `$ARGUMENTS`, the Epic, and the brief:

- **With an approved brief**, each line of `## Goals` restates one goal from the brief's
  `## Goals`, narrowed to this feature. A goal that restates none is cut; if that leaves
  the feature serving no goal of the brief, say so at Step 5 as a question for
  `{{roles.product_owner}}`.
- **Given an Epic key**, `## Summary` opens with the line `Epic: <KEY>`, and the design
  keeps the Epic's `SM<n>` and `NFR<n>` IDs, as the gate requires.

**Then survey, before reading any code.** Name two or three real systems that solve the
whole problem — documented standards, framework conventions, well-known implementations —
using WebSearch and WebFetch here, scoped by the request and the Epic alone. Write the
design doc's `# <title>` line and its `## Survey` section, each system with its source, to
`{{design_dir}}/<slug>.md` **before any `Explore` agent launches**: a survey written after
the code reads starts from what the code already does.

## Step 3 — Inventory the current state, then write the design

Delegate breadth to `Explore` agents, several in parallel across distinct questions, each
scoped by the request and the Epic: where each existing feature the new one overlaps or
depends on lives, its callers and configuration, and its tests. Search Jira too —
`project = {{jira_project}} AND text ~ "<distinctive term>"` — for epics and stories in the
same area. Read the code the agents point to; do not design from file names.

`## Current state` names, for each such feature, the `file:line` or Jira key behind it. A
feature with neither is not yet found: look again rather than write it unsourced.

Then write every other section the gate's **Sections** list names, in its order, under its
**Section rules** and **Work plan** rules — `## Threat model` only with `security` in
`{{disciplines}}`. `## Decision` reads `Pending — <tech lead>.` A value neither the request,
the Epic, the brief, nor the code supplies is a proposal: write it, mark it `(proposed)`,
and list it at Step 5.

With `adr_dir` unset, stop before writing a `- Costly to reverse:` line, naming `adr_dir`:
the choice has no record to point to, and the gate fails the design. Otherwise write one
ADR per such line, in the gate's MADR form and at the path the line names, with
`status: proposed`, `date` from `date +%F`, and the tech lead as `decision-makers`. Number
them by the gate's **ADRs** numbering rule after `git fetch`; each file's `<title>` is what
`design_check.py slug` prints for the choice, handed over as in Step 1.
Stop, as in Step 1, when any ADR's path is ignored.

Before Step 4, check the doc against every rule of the gate and fix what fails: the
reviewer's scarcest output is the finding a grep would not have found.

## Step 4 — Review it cold

Launch the `feature-design-adversary` agent. **The delegation contains only the design
doc's absolute path** — nothing about the request, the survey, what changed, or where the
risk is. Every round is delegated the same way.

Fix every BLOCKER, and every MAJOR that names a gate rule the doc fails; a MAJOR you
disagree with is noted at Step 5, not argued with the reviewer. A round's fixes are
reviewed by the next round, inside the count. **The review stops at a round with zero
BLOCKERs that left nothing to fix, or after the third round.** At the cap, bring the
remaining findings, and any fix no round has reviewed, to Rob as they stand, and present
nothing until he answers. Before a third round, apply `deliver`'s revert rule: when the
second round's findings are mostly against the first round's fixes, revert them and take
another approach.

Then the gate's step 8 review: ask the person running the session, in one message, for the
name of each engineer outside the immediate team who reviewed the design against its
requirements and non-functional thresholds. A name is never defaulted. With none, the
criterion passes only while `{{exceptions_log}}` holds an unexpired row for rule book
Phase 3 step 8 covering designs; without one, Step 5 shows criterion 1 open.

An edit after a review re-runs that review, the cold one and step 8's alike, as the gate's
**Approvers** section states.

## Step 5 — Present, then stop

Check every exit criterion of the gate against the doc, its ADRs, and Step 4. Then present,
printing each role per `gates/project-config.md`:

- the design doc's path and line count, and each ADR's path
- every `(proposed)` value, one line each
- the review's rounds and its last verdict, and each MAJOR left unfixed with the reason
- each exit criterion and how it stands, with the approvals open

**Ask `{{roles.qa}}` to approve `## Test strategy` and `{{roles.product_owner}}` to approve
`## Goals` and `## Non-goals`, then wait on `{{roles.tech_lead}}`**, whose approval counts
only once both have approved; a rejection or a hold counts at any time, since only the
tech lead decides. One person holding several roles gives them in one answer. A rejection
from QA or the product owner is a rework answer for the section they reject.

The tech lead's answer is one of `plan-project` Step 4's four:

- **Approve** or **reject** — a decision, and a final one. Go to Step 6. An approval is
  recorded only once every exit criterion other than the approvals passes — the cold
  review ended with no open BLOCKER, step 8's review or its exception, every ADR, every
  NFR line. While one is open, say which, and the answer is rework, not a decision.
- **Rework** — changes asked for, which is not a decision. Revise the design and its ADRs,
  re-check the gate's rules, and run one `feature-design-adversary` round outside Step 4's
  three-round count; its BLOCKERs go to the tech lead. Ask again for step 8's reviewers, as
  in Step 4. An edit to an approved section voids that approval and goes back to its
  approver. Then `git fetch`, re-check against a moved parent as Step 6 does, and present
  again.
- **Hold** — the tech lead defers. **Record nothing and commit nothing**: the doc stays
  `Pending` and its ADRs `proposed` in the working tree, and a later run presents them
  again.

A clarifying question is not an answer. An answer relayed by the person running the session
is printed as relayed.

## Step 6 — Record the decision and commit

Run `git fetch` first. When `origin/design/<slug>` now exists, stop and ask, as Step 1 does.
When `origin/{{parent_branch_default}}` moved since the base — the commit Step 1 recorded,
or the latest one recorded here, which replaces it — record its new commit as the base,
since the branch is cut from the base and not from HEAD. Re-run Step 1's stops other than
HEAD equaling `origin/{{parent_branch_default}}`, and stop when `git cat-file -e
<base>:{{design_dir}}/<slug>.md` succeeds: the design is already committed there. Re-check
each `## Current state` claim against the base, renumber the ADRs when a new record took
one of their numbers, and present again before recording anything. What an edit or a
renumber re-runs, and which approvals it voids, is the gate's **Approvers** section's.

**Before editing any file**, write everything the commit needs to the directory
`git rev-parse --path-format=absolute --git-path design-feature` names, as git's sequencer
keeps a commit's `message` and `author-script` where it can finish without the session that
began it:

- `presented/` — the design doc and every ADR as Step 5 presented them, at their
  repository paths
- `slug`, and `base` — the latest base recorded
- `decision` — the full text replacing `Pending — <tech lead>.`, every line of it: the
  decision as the gate's **Decision** section words it, dated from `date +%F`, with its
  relayed suffix where it applies, and a rejection's reason line
- `status` — `accepted` or `rejected`
- `message` — the commit message: `Record the <title> design and the tech lead's
  decision`, a blank line, then one `Reviewed-by: <name>` trailer per step 8 reviewer Step 4
  named

Then write `decision` under `## Decision`. Set each ADR's `status` to `accepted` for an
approval or `rejected` for a rejection, and its `date` to the same date. An approval
confirms every `(proposed)` value as written, so remove those marks with it; a rejection
keeps them, since nothing was confirmed. A rejected design is committed too, its ADRs
keeping their numbers: it is the record of the stop.

Write each file with the Write tool, per **Untrusted text** in `gates/project-config.md`:
the title and the names are free text. Then cut the branch from `base`, which the fetch above
confirmed is `origin/{{parent_branch_default}}`, and commit the design doc and its ADRs
alone, from `message`:

```bash
git switch -c design/<slug> <base>
git add -- {{design_dir}}/<slug>.md <each ADR path>
git commit -F "$(git rev-parse --path-format=absolute --git-path design-feature)/message" -- {{design_dir}}/<slug>.md <each ADR path>
```

Remove the state directory once the commit succeeds. When the commit fails — a hook rejects
it, say — fix what it names and commit again; the tech lead's answer stands. If that cannot
be done in this run, stop with the directory in place and say so: the next run continues or
aborts it, as `git rebase --continue` and `--abort` do.

**Do not push.** Report the branch, the commit, and the decision, and leave publishing it to
the person running the session. The design reaches `{{parent_branch_default}}` by an
ordinary pull request, as `plan-project`'s brief does: `ship-pr` needs a ticket, and the
design precedes its tickets.
