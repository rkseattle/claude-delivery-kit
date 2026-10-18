---
name: incident-review
description: Run the rule book's Phase 7 blameless incident review — timeline, impact, root cause, contributing factors, and follow-ups — record whether it started within five working days, create each follow-up ticket only once the service owner approves it, and commit the review on its own branch.
argument-hint: <incident, a few words> <incident date YYYY-MM-DD>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Review the incident: $ARGUMENTS

This skill is the rule book's Phase 7 step 3, after service is restored: "hold a blameless
review within five working days. Record cause, impact, and follow-up tickets." It writes one
file, `{{incident_reviews_dir}}/<date>-<slug>.md`, creates the follow-up tickets
`{{roles.service_owner}}` approves, and commits the file on `incident/<date>-<slug>`, cut from
`origin/{{parent_branch_default}}` — never on `{{parent_branch_default}}` itself. No push:
the review reaches the parent branch by an ordinary pull request, as `plan-project`'s brief
does.

The form is Google SRE's blameless postmortem (*Site Reliability Engineering*, ch. 15) with
the sections of Atlassian's incident handbook, whose follow-up actions are approved by an
accountable owner before they are tracked.

## Step 1 — Read the configuration and check the prerequisites

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `incident_reviews_dir`, `secret_scan_command`, and `roles`.

`$ARGUMENTS` is the incident, in a few words, then its date, the UTC date it began; with
either missing, ask for it in one line before anything else. The slug is those words in lowercase kebab-case. The
start date is today's in UTC, from `date -u +%F`, as the timeline is in UTC, unless the
review file already exists uncommitted, as below: then it is that file's `Review started:`
date, since the review started then.

Stop, and say why in one line, when:

- **`.claude/state/current-plan.json` exists without `"paused": true`.** A delivery run is
  in flight, and the branch guard moves HEAD back to its branch after any command that
  leaves it, which would undo Step 5's switch. A file that does not parse stops too.
- **`{{incident_reviews_dir}}` is `none`**, absent or set so, or this prints anything but
  `ok`. The review has nowhere to live, and the path is written unquoted below.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/incident-review/scripts/incident_check.py" reviews-dir --value "{{incident_reviews_dir}}"
  ```

- **Either check below exits non-zero** — an `INVALID:` line for a date that is not a real
  `YYYY-MM-DD`, an incident after the start, or a slug that is not lowercase kebab-case;
  any other failure is named as it printed:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/incident-review/scripts/incident_check.py" working-days --incident <date> --start <start date>
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/incident-review/scripts/incident_check.py" branch --date <date> --slug <slug>
  ```

- **`git check-ignore -v {{incident_reviews_dir}}/<date>-<slug>.md` matches.** The review is
  committed in Step 5; name the rule it printed.
- **After `git fetch origin`, `incident/<date>-<slug>` or `origin/incident/<date>-<slug>`
  exists**, other than the interrupted commit below. Ask rather than reuse it.
- **`git cat-file -e HEAD:{{incident_reviews_dir}}/<date>-<slug>.md` or the same against
  `origin/{{parent_branch_default}}` succeeds.** The review is already committed; ask
  rather than write over the record and its follow-up answers.

An existing `{{incident_reviews_dir}}/<date>-<slug>.md` that HEAD does not hold
(`git cat-file -e HEAD:{{incident_reviews_dir}}/<date>-<slug>.md` fails) is an earlier,
uncommitted run, stopped at Step 4 or 5: read it and continue from it, keeping
its header and every follow-up key and answer it records, rather than writing over it.
When the local branch `incident/<date>-<slug>` also exists and
`git rev-list --count origin/{{parent_branch_default}}..incident/<date>-<slug>` prints `0`,
Step 5's commit was interrupted after its switch, as `git rebase --continue` resumes a
stopped rebase: switch to that branch and finish Step 5's commit; the branch stop above does
not apply to it.

The working-days check prints the working days from the incident to the start date and
`on time` or `late`: late when more than five, counted Monday to Friday after the incident
date. Both go in the review's header as printed.

## Step 2 — Gather the facts

Read what the checkout holds about the incident window: `git log` around the date, the
changes deployed, and the CI runs (`gh run list`). Ask the person running the session for
what it does not — alerts, detection and restore times, who was affected and for how long —
in one message. A clarifying answer is a fact; a fact nobody can supply is written as
`unknown`, never guessed.

## Step 3 — Write the review

Write `{{incident_reviews_dir}}/<date>-<slug>.md`, every section in this order:

```markdown
# Incident review — <incident>

Incident: <date>
Review started: <start date> — <n> working days after the incident, <on time or late>
Service owner: <name>

## Timeline
## Impact
## Root cause
## Contributing factors
## Follow-ups
```

- **Timeline** — one line per event, `<YYYY-MM-DD HH:MM UTC> — <event>`, from the first
  trigger through detection, response, and restoration.
- **Impact** — who and what was affected, for how long, and how it was measured.
- **Root cause** — the condition in the system whose removal prevents a recurrence, found by
  the kit's root-cause discipline (`${CLAUDE_PLUGIN_ROOT}/skills/deliver/SKILL.md`, "Root
  cause, then pattern spread"): ask why the failure was possible until the answer is a
  condition of the system, not an action. Then grep the codebase for other live instances
  of that condition, and list each, with its path, as a follow-up.
- **Contributing factors** — the other conditions that made it worse, longer, or harder to
  see: a missing alert, an untested path, an unclear runbook.
- **Follow-ups** — one line each,
  `- <summary> — AC: <criterion> [verify: <tier> @ <evidence>] — proposed`, from the root
  cause, every instance its grep found, and each contributing factor. The criterion is the
  one that would show the follow-up done, its tier one `{{verification_tiers}}` declares,
  written here so that what the service owner approves is what a resumed run tickets.

`<name>` is the service owner as `roles` names them, or with none there, the person running
the session by git `user.name` — never the word "you", which means nothing in a committed
record.

**Blameless means systems and conditions.** `Root cause` and `Contributing factors` name
components, configurations, processes, and gaps — never a person, a handle, or a role
standing in for one ("the on-call engineer forgot"). A human action is written as what the
system allowed: "the deploy tool accepted a config with no validation". Before Step 4, check
the file — and again before Step 5 on a re-run, since it may have been edited — with
`grep -n -i -w -F` for each word of each name — in `roles`, git `user.name`,
and the authors of the `git log` Step 2 read — so a handle such as `ed` never matches
`deployed` and `Rob Kruy` is found as `Rob`. Rewrite every line it finds in those two
sections that names a person.

## Step 4 — Propose the follow-ups to the service owner

Skip this step when no line is still `— proposed`, as on a re-run that only finishes
Step 5. Otherwise present to `{{roles.service_owner}}`, printed per
`gates/project-config.md`: the review's
path, its `Root cause`, and each follow-up, numbered, with its criterion as the file records
it. Then stop and wait. A summary, criterion, or verify tag the service owner changes is
rewritten in its line before the line records the approval.

Each follow-up is approved, declined, or held on its own. Only an explicit approval of that
follow-up counts; a clarifying question is not one, and only the service owner's answer
counts — one relayed by the person running the session is printed as relayed. **No Jira
ticket is created before its approval.** Mark each line with its answer: an approved one
`— approved by <name> <YYYY-MM-DD>`, a declined one `— declined by <name> <YYYY-MM-DD>`,
each with `, relayed by <git user.name>` for a relayed answer, and a held one left
`— proposed`.

## Step 5 — Create the approved tickets, then commit

For each approved follow-up whose line has no key yet, in order, first search
`project = {{jira_project}} AND labels = incident-follow-up AND text ~ "<date>-<slug>"` for
its summary. A match whose description names this review's path is the ticket an
interrupted run created, and its key is written to the line instead; another incident's
ticket with the same summary is not. Otherwise
create it as `write-tickets` Step 8 creates a ticket: look up
`{{jira_project}}`'s issue types first and use `Task`, never a guessed name or ID. Give it:

- the summary its line records;
- the label `incident-follow-up`;
- a description of `## Context`, naming the review's path and the branch it will be
  committed on, and
  `## Acceptance criteria` holding the criterion its line records as one `- AC1:` line
  ending in its `[verify: <tier> @ <evidence>]` tag, the tier one `{{verification_tiers}}`
  declares, the tag inside a code span as `write-tickets` writes it.

Read each ticket back with `jira_get_issue` and confirm it carries `incident-follow-up` and
its `[verify: …]` tag whole; fix either once if it does not, and report it if it still does
not. Append each key to its line, `— approved by <name> <YYYY-MM-DD> — <KEY>`, as it is
created, so a stopped run never creates one twice.

**While any follow-up is held, stop here and commit nothing**, as `plan-project`'s Hold
does: the review stays uncommitted in the working tree, and a re-run continues from it,
presenting only the lines still `— proposed`. Report the path and the held lines.

Otherwise, since Step 4's wait may have been long, repeat Step 1's first stop — a plan now
in flight would undo the switch below — then run `git fetch origin` again; if
`origin/incident/<date>-<slug>` now exists, stop and ask, as Step 1 does. Then cut the branch
from the freshly fetched parent and commit the review alone:

```bash
git switch -c incident/<date>-<slug> origin/{{parent_branch_default}}
git add {{incident_reviews_dir}}/<date>-<slug>.md
```

Before the commit, unless `{{secret_scan_command}}` is `none`, run
`${CLAUDE_PLUGIN_ROOT}/gates/definition-of-done.md` step 7's secret scan of the staged
additions, its block exactly as that step writes it, so the record is held to the same scan
as every commit.

Anything but `clean` stops the skill before the commit: report each `rule file:line` it
printed, never the text, and rewrite those lines to name the credential rather than hold it.
A re-run finishes the commit as Step 1 describes: it stages the rewritten file again with
`git add`, since the scan reads the index, then scans again. Then:

```bash
git commit -m "Record the incident review <date>-<slug>" -- {{incident_reviews_dir}}/<date>-<slug>.md
```

A failed switch or commit stops the skill with the file in place; a re-run continues from
it, finishing the commit as Step 1 describes. Do not push. Report the path, the commit,
`on time` or `late`, and each follow-up with its key or answer, and say that HEAD is left on
`incident/<date>-<slug>`, to be switched back from when the review is pushed.
