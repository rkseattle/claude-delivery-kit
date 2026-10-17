---
name: maintenance-review
description: Run the rule book's Phase 7 ongoing checks — owner and on-call rota, incoming work by maintenance type, the preventive share of the last iteration, outdated dependencies, vulnerabilities past their patch SLA, stale runbooks, alerts routed to no person, and old incident follow-ups, plus the security, data-ml, and SRE maintenance addenda — report them, and create each proposed ticket only once the service owner approves it.
argument-hint: (no arguments)
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

Review maintenance for this project.

This skill is the rule book's Phase 7, steps 1, 2 and 4–6, and its ongoing checks, with the
maintenance lines of Appendix B1, B2 and B5. It prints a report in the session and stops for
`{{roles.service_owner}}`. **It writes no file, commits nothing, and creates no Jira ticket
before the service owner approves that ticket**: every command below only reads, and the
report lives in the conversation, as `plan-work` presents a plan. What it then creates is
the approved tickets, each labeled with its ISO/IEC/IEEE 14764 maintenance type —
corrective, adaptive, perfective, or preventive — the four the rule book's step 2 names.

## Step 1 — Read the configuration

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it. Read
`${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's optional
keys are `on_call`, `iteration_days`, `debt_share_target`, `dependency_outdated_command`,
`patch_sla_days`, `runbooks_dir`, `alert_routes_command`, `roles`, and `disciplines`, with
the keys its named disciplines need here: `alert_rules_dir` for `sre`, and
`drift_check_command` and `drift_threshold` for `data-ml`. A key no named discipline needs is
not used, so it is not announced.

With the project root written as its absolute path, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/maintenance-review/scripts/maintenance_check.py" config --config "<project root>/.claude/project.json"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" disciplines --config "<project root>/.claude/project.json" --gate maintenance
date -u +%F
```

Stop, and say why in one line, naming each `INVALID:` line, when the first prints one or the
second prints anything but `ok`. The second holds every discipline's keys for every gate:
with `security`, `patch_sla_days` is required; with `sre`, `alert_rules_dir`; with
`data-ml`, `drift_check_command` and `drift_threshold`. The first prints each general key as
`<key>\t<value>`, the value as JSON, its default or `"none"` when unset; those values are
the ones every step below uses, and the announcement `gates/project-config.md` asks for is
made from them.
`date -u +%F` is `<today>`, written out in full wherever it appears below.

Every command below runs from the project root, which the checks read `{{runbooks_dir}}` and
git's paths against. **Every configured command runs in a subshell** —
`( {{command}} )`, as `release-readiness` runs its suites — so a `cd` or `export` inside it
cannot move or change the shell for the commands after it. Where a command's output is piped
into a check, the pipeline runs under `set -o pipefail` inside its own subshell, so the
command's failure is not hidden behind the check's success.

## Step 2 — Gather

Every read here is a read and nothing more: no command below writes a file, and none of
them changes Jira. A read that errors, times out, or stops short is a **failed read**: its
section in Step 3 names it and what it printed, and is never written as empty, since an
empty section reads as nothing to do.

**Jira**, through the Atlassian MCP's `jira_search`, every query starting
`project = {{jira_project}} AND`. Page each query until every result is read, with
`page_token` where the result gives one and `start_at` otherwise; count the issues read,
since this connector returns `"total": -1` and a `total` field is never a count.

- **Open, by type** — four queries, `statusCategory != Done AND labels = <type>`, for
  `corrective`, `adaptive`, `perfective`, and `preventive`.
- **Open, unclassified** — `statusCategory != Done AND (labels is EMPTY OR labels not in
  (corrective, adaptive, perfective, preventive))`, keeping each key and summary.
- **Resolved this iteration** — `statusCategory = Done AND statusCategoryChangedDate >=
  -{{iteration_days}}d`, then the same with `AND labels = preventive`, by status category as
  every other query here, since a workflow can reach done without setting a resolution. Their counts are `<resolved>` and `<preventive>`.
- **Old incident follow-ups** — `statusCategory != Done AND labels = incident-follow-up AND
  created < -30d`, keeping each key, summary, and created date. The `<` keeps an issue
  created exactly 30 days ago out, as "more than 30 days" asks.

**Commands**, each unless its key printed `"none"` in Step 1; a non-zero exit is a failed
read, except where the first bullet says otherwise.

- **Outdated dependencies** — `( {{dependency_outdated_command}} )`, keeping its output
  whole. Exit 0, and exit 1 with output listing packages, are results: `npm outdated`,
  `yarn outdated`, and `bundle outdated` exit 1 when anything is outdated. Any other exit,
  and exit 1 whose output is an error rather than a package list, is a failed read, so a
  missing tool or a broken lockfile never reads as a list of dependencies.
- **Vulnerabilities past the SLA**, with `patch_sla_days` set:

  ```bash
  ( set -o pipefail; gh api --paginate --slurp "repos/{{repo_slug}}/dependabot/alerts?state=open&per_page=100" | python3 "${CLAUDE_PLUGIN_ROOT}/skills/maintenance-review/scripts/maintenance_check.py" alerts --config "<project root>/.claude/project.json" --today <today> )
  ```

  Each line is `<severity>`, `<age in days>`, `<package>`, `<advisory>`, `<manifest>`,
  `<url>`, by tabs,
  Critical first, then oldest first. A `gh` error — a 403 for a token without
  `security_events`, a 404 where Dependabot alerts are off — is a failed read, never zero
  alerts.
- **Stale runbooks**, with `runbooks_dir` set:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/maintenance-review/scripts/maintenance_check.py" runbooks --config "<project root>/.claude/project.json" --today <today>
  ```

  Each line is a runbook last committed more than 90 days ago, the rule book's "at least once
  a quarter", with that date, or `uncommitted`. In a shallow clone it prints `INVALID:`
  instead, since every file there reads as last committed at the clone's boundary: a failed
  read, fixed by `git fetch --unshallow`.
- **Alert routes**, with `alert_routes_command` set:

  ```bash
  ( set -o pipefail; ( {{alert_routes_command}} ) | python3 "${CLAUDE_PLUGIN_ROOT}/skills/maintenance-review/scripts/maintenance_check.py" routes --config "<project root>/.claude/project.json" )
  ```

  Each line is a `<rule>` and the `<target>` that is not a person on `{{on_call}}`, matched
  exactly, or `malformed` and a line that is not one rule and one target. With `on_call`
  unset, every route is listed, since no target is a person on a rota nobody named.
- **Drift**, with `data-ml`:

  ```bash
  ( set -o pipefail; ( {{drift_check_command}} ) | python3 "${CLAUDE_PLUGIN_ROOT}/skills/maintenance-review/scripts/maintenance_check.py" drift --config "<project root>/.claude/project.json" )
  ```

  `within <n>` or `over <n>`; any non-zero exit is a failed read.
- **Alert rules**, with `sre` — Appendix B5: "each alert must map to an SLO or a documented
  failure mode and link to a runbook". Read every `.yml` and `.yaml` file under
  `{{alert_rules_dir}}` as Prometheus alerting rules: each `- alert: <name>` entry under a
  group's `rules`. An entry links a runbook when its `annotations` hold `runbook_url`, the
  kube-prometheus convention, or `runbook`, and maps to an SLO when its `labels` or `annotations` hold
  `slo`, the label Pyrra gives the alerts it generates, or `sloth_slo`, Sloth's. With no SLO,
  its linked runbook is the documented failure mode B5 accepts in an SLO's place, so the rule
  B5 sets every entry is a `runbook_url`: keep each entry without one, with the file, the
  alert name, and whether it maps to an SLO. A file holding no `alert:` entry is listed as
  such, since a rule in another format is not one this check can read. A missing
  `{{alert_rules_dir}}`, or one holding no `.yml` or `.yaml` file, is a failed read, never
  `none found`. This check and the reading of the outdated-dependency output are by eye, not
  by the script: YAML is not in Python's standard library, which every kit script keeps to,
  and each dependency tool prints its own table.

## Step 3 — Report

Print the report in the session, in this order, every section present but the three a
discipline adds when that discipline is not named. A section whose key
is `none` says so in one line and how to set it; a failed read says what failed.

```markdown
# Maintenance review — <today>

## Ownership
## Incoming work
## Debt share
## Dependencies
## Vulnerabilities past the patch SLA
## Critical vulnerabilities past the patch SLA
## Runbooks
## Alert routes
## Incident follow-ups
## Alert rules
## Drift
```

- **Ownership** — `service owner: <person>`, printed per `gates/project-config.md`, or with
  no `service_owner` in `roles`, `service owner: unset — roles.service_owner is absent, so
  you hold the role this session`, since a named owner is what Phase 7 step 1 asks; and
  `on-call: <each handle>`, or `on-call: unset — on_call is none`.
- **Incoming work** — the count for each of the four types, then each unclassified open
  issue as `<KEY> — <summary>`. The skill proposes no label for them: classifying incoming
  work is the service owner's call, and relabeling someone else's issue is a Jira write.
- **Debt share** — the share of issues resolved in the last `{{iteration_days}}` days that
  carry `preventive`, from:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/maintenance-review/scripts/maintenance_check.py" share --config "<project root>/.claude/project.json" --resolved <resolved> --preventive <preventive>
  ```

  It prints the share, rounded down to one decimal, then `meets <T>%` or `below <T>%`
  against `{{debt_share_target}}`, or the share alone when that is `none`. With nothing
  resolved in the window it prints `no issues resolved`, and the section says so. The rule
  book's step 5 calls 10–20% "a common starting point", which is why no default is assumed.
- **Dependencies** — the command's output, in a code block.
- **Vulnerabilities past the patch SLA** — each `alerts` line. With `patch_sla_days` `none`:
  `unset — patch_sla_days is none, so no alert is measured against a patch SLA`.
- **Critical vulnerabilities past the patch SLA** — with `security` only, and the heading
  left out otherwise: the `critical` lines alone, Appendix B1's "Critical vulnerabilities
  are patched within the organization's SLA".
- **Runbooks**, **Alert routes** — each line the check printed.
- **Incident follow-ups** — each as `<KEY> — <summary> — created <date>`: the rule book's
  check that incident reviews have closed follow-ups.
- **Alert rules** — with `sre` only, the heading left out otherwise: each entry Step 2 kept.
- **Drift** — with `data-ml` only, the heading left out otherwise: `within` or `over`, the
  number, and `{{drift_threshold}}`.

A section with nothing to report says `none found`, which is a different line from a key
that is unset and from a failed read.

## Step 4 — Propose the tickets

From the report, propose one ticket per finding below, numbered, each with its type label,
its finding key, the summary its row gives, and one acceptance criterion with a
`[verify: <tier> @ <evidence>]` tag, its tier one `{{verification_tiers}}` declares. The
finding key is what an earlier review's ticket is found by, so it is written exactly as the
row gives it, never reworded. More than ten outdated packages get the one `dependencies`
ticket **instead of** a ticket each:

| Finding | Type | Finding key | Summary |
| --- | --- | --- | --- |
| an alert past its SLA | `corrective` | `alert <package> <advisory> <manifest>` | Patch `<package>` for `<advisory>` in `<manifest>` |
| drift over its threshold | `corrective` | `drift` | Retrain or roll back the model past its drift threshold |
| an outdated dependency | `adaptive` | `dependency <package>` | Update `<package>` |
| more than ten outdated | `adaptive` | `dependencies` | Update the outdated dependencies |
| a stale runbook | `preventive` | `runbook <path>` | Review the runbook `<path>` |
| a route to no person | `preventive` | `route <rule>` | Route the alert `<rule>` to a person on call |
| an alert rule with no runbook | `preventive` | `alert-rule <file> <name>` | Link the alert `<name>` to a runbook |

Drift's ticket is the retraining or rollback Appendix B2 asks a threshold to trigger. A
`malformed` route line and an `uncommitted` runbook get no ticket: the first is the routes
command's output to fix, and the second exists only in this checkout.

**Before presenting, find what is already tracked.** Search
`project = {{jira_project}} AND labels = maintenance-review AND statusCategory != Done`,
paging as Step 2's queries do, and read each result's description with `jira_get_issue`. A
proposal whose finding key is exactly the code span on an open ticket's `Finding:` line is
already tracked:
list it with that key and propose no ticket for it. The query names no finding key, so no
character in a path or alert name can break it or widen it into a wildcard. A failed search
is a failed read, and then no ticket is proposed at all, since none can be shown not to
exist already.

Present them to `{{roles.service_owner}}`, printed per `gates/project-config.md`, and stop
and wait. A label, criterion, or tag the service owner changes is changed in the proposal
before it is approved; the summary and finding key stay as their row gives them. Each ticket
is approved, declined, or held on its own; only an explicit approval of that ticket counts —
a clarifying question is not one, and only the service owner's answer counts, one relayed by
the person running the session printed as relayed. **No ticket is created before its
approval**, and none is created for a declined or held one. Ownership, the debt share,
unclassified issues, and old follow-ups get no ticket: they are settings to change or work
already tracked.

## Step 5 — Create the approved tickets

Since Step 4's wait may have been long, repeat its search first; an approved proposal whose
finding key is now an open ticket's `Finding:` line is reported with that key and not
created. Create each other approved ticket, in order, as `incident-review` Step 5 creates a
follow-up: look up `{{jira_project}}`'s issue types first
and use `Task`, never a guessed name or ID. Give it:

- the approved summary;
- the labels `<type>` and `maintenance-review`;
- a description of `## Context`, naming the report's date and its finding line, then
  ``Finding: `<finding key>` `` on a line of its own — the key inside a code span, which
  the Atlassian connector's read conversion keeps verbatim, as `write-tickets` relies on —
  and
  `## Acceptance criteria` holding the approved criterion as one `- AC1:` line ending in
  its `[verify: <tier> @ <evidence>]` tag, the tag inside a code span as `write-tickets`
  writes it.

Read each ticket back with `jira_get_issue` and confirm it carries both labels, its
`[verify: …]` tag whole, and its `Finding:` code span exactly; fix any once if it does not, and report it if it still does
not. Then report each approved ticket with its key, and each declined or held one with its
answer. Nothing else changes: no file, no commit, no other Jira write.
