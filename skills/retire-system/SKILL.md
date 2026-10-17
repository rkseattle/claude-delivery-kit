---
name: retire-system
description: Run the rule book's Phase 7 system retirement — write a record with user notice, data, infrastructure, and credentials sections, draft the notice, list every data store, resource, and credential the repository names, mark each section done only once the service owner confirms it, and commit the record on its own branch once all four are done. Runs no removal itself.
argument-hint: <system name, lowercase kebab-case>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Retire the system: $ARGUMENTS

This skill is the rule book's Phase 7 step 7, the service owner's under Appendix A: "When
retiring a system, notify users, migrate or archive data, and remove infrastructure and
credentials." It writes one file, `{{retirements_dir}}/<name>.md`, and commits it on
`retire/<name>`, cut from `origin/{{parent_branch_default}}` — never on
`{{parent_branch_default}}` itself. No push: the record reaches the parent branch by an
ordinary pull request, as `incident-review`'s does.

The sections follow NIST SP 800-37 Rev. 2's system disposal task (M-7): notify the users and
plan the transition, preserve or migrate the information, sanitize the media as NIST SP 800-88
Rev. 1 describes, and remove the system's components, with credentials disabled and revoked
as NIST SP 800-53 AC-2(3) and IA-5 require once they are no longer needed.

**Every removal is the service owner's, never this skill's.** It sends no notice and runs no
command that deletes, destroys, drops, revokes, or rotates anything — no `terraform destroy`,
`kubectl delete`, `helm uninstall`, `gh secret delete`, cloud CLI `delete`, `rm`, or
`revoke`, and no SQL `DROP` — whoever asks. It reads the repository, writes the record, and
records what the service owner confirms was done.

## Step 1 — Read the configuration and check the prerequisites

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `retirements_dir`, `secret_scan_command`, and `roles`.

`$ARGUMENTS` is the system's name; with none, ask for it in one line before anything else.
`<today>` is `date -u +%F`, written out in full wherever it appears below. Every command
below runs from the project root, which `{{retirements_dir}}` is relative to.

Stop, and say why in one line, when:

- **`.claude/state/current-plan.json` exists without `"paused": true`.** A delivery run is
  in flight, and the branch guard moves HEAD back to its branch after any command that
  leaves it, which would undo Step 5's switch. A file that does not parse stops too.
- **Either check below prints anything but `ok` and `retire/<name>`** — an `INVALID:` line
  for a `retirements_dir` that is `none`, absent, or not a relative path inside the
  repository, or a name that is not lowercase kebab-case. With the project root written as
  its absolute path:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/retire-system/scripts/retire_check.py" retirements-dir --config "<project root>/.claude/project.json"
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/retire-system/scripts/retire_check.py" name --value "<name>"
  ```

- **`git check-ignore -v {{retirements_dir}}/<name>.md` matches.** The record is committed in
  Step 5; name the rule it printed.
- **After `git fetch origin`, `retire/<name>` or `origin/retire/<name>` exists**, other than
  the interrupted commit below. Ask rather than reuse it.
- **`git cat-file -e HEAD:{{retirements_dir}}/<name>.md` or the same against
  `origin/{{parent_branch_default}}` succeeds.** The record is already committed; ask rather
  than write over it.

An existing `{{retirements_dir}}/<name>.md` that HEAD does not hold is an earlier,
uncommitted run, stopped while sections were pending: read it and continue at Step 4,
keeping every checklist item, status, and confirmation it records, rather than writing over
it. When the local branch `retire/<name>` also exists and
`git rev-list --count origin/{{parent_branch_default}}..retire/<name>` prints `0`, Step 5's
commit was interrupted after its switch: switch to that branch, run Step 4's check again,
and finish Step 5's commit only if it still prints `done`; the branch stop above does not
apply to it.

## Step 2 — Inventory what the repository names

Search the checkout with Grep and Glob, reading every match in context, for what the system
holds. Record each finding by **name and location only**, as `<name> — <path>:<line>`.
**Never copy a value**: no connection string, key, token, or password enters the record,
since a committed secret is a leaked one, as OWASP's Secrets Management Cheat Sheet treats
it. A finding whose name is itself a secret is recorded by its key or variable name.

- **Data stores** — what holds data: Terraform `resource` blocks and CloudFormation
  resources of a database, cache, queue, bucket, or table type (such as `aws_db_instance`,
  `aws_s3_bucket`, `AWS::RDS::DBInstance`, `AWS::S3::Bucket`, `AWS::DynamoDB::Table`),
  docker-compose services running a database, cache, or queue image and its `volumes:`,
  Kubernetes `PersistentVolumeClaim`s, and connection variables named `*_URL`, `*_DSN`,
  `DATABASE_*`, or `REDIS_*`.
- **Infrastructure** — every other Terraform `resource`, CloudFormation resource,
  docker-compose service, Kubernetes or Helm `kind:`, DNS record, CI deploy job, and
  scheduled workflow. A Terraform `data` block reads something this system does not own, so
  it is never an item: it is named in the notice's audience if another team owns it.
- **Credentials** — each GitHub Actions `secrets.<NAME>`, each key in `.env.example` or a
  similar template, and each variable or setting named with `KEY`, `TOKEN`, `SECRET`,
  `PASSWORD`, or `CREDENTIAL`.

A category with no finding gets the one item `- [ ] none found in the repository; nothing
held elsewhere`, so every section has an item to confirm, and the service owner adds anything
held outside the repository — a vendor account, a dashboard, a store listing — in Step 4.

## Step 3 — Write the record

Write `{{retirements_dir}}/<name>.md`, every section in this order:

```markdown
# Retirement — <name>

Service owner: <service owner>
Started: <today>

## User notice

Status: pending

- [ ] Notice sent to <each user group>
- [ ] Notice period ended
<the drafted notice, in a fenced block>

## Data

Status: pending

- [ ] <data store> — <path>:<line> — migrated to <where> or archived at <where>

## Infrastructure

Status: pending

- [ ] <resource> — <path>:<line> — removed

## Credentials

Status: pending

- [ ] <credential name> — <path>:<line> — revoked
```

- **User notice** — the drafted notice: whom it goes to — each user group and dependent team
  the repository names, as consumers in its docs, API clients, or owners of the resources a
  `data` block reads — what is retiring, when, what replaces it or where data goes, and whom
  to contact, with every fact it cannot know — a date, a replacement, a contact, a group —
  written as exactly `<to confirm>`, the one marker Step 4's check knows. It is a draft;
  this skill never sends it.
- **Data**, **Infrastructure**, **Credentials** — one item per Step 2 finding.

The record holds only the lines this template writes: outside the fenced notice, every line
is the title, the `Service owner:` and `Started:` lines, a section heading, a `Status:` or
`Confirmed:` line, a `- [ ] <item>` or `- [x] <item>` line, or blank, and Step 4's check
refuses any other. A note the service owner adds goes into an item's text.

`<service owner>` is the service owner as `roles` names them, or with none there, the person
running the session by git `user.name` — never the word "you", which means nothing in a
committed record.

## Step 4 — Confirm each section with the service owner

Present to `{{roles.service_owner}}`, printed per `gates/project-config.md`: the record's
path and each section still `Status: pending`, with its items. Then stop and wait. An item
the service owner adds, removes, or rewrites is changed in the record before anything is
marked.

**A section becomes `done` only on the service owner's explicit confirmation that every item
in it is complete.** A clarifying question is not one, nor is a confirmation of some items;
and only the service owner's answer counts — one relayed by the person running the session
is recorded as relayed. On a confirmation, tick that section's items, set `Status: done`,
and add `Confirmed: <service owner> <today>`, with `, relayed by <git user.name>` for a
relayed answer. Confirming a section also writes in what the service owner says was done, so
no `<placeholder>` is left in it: each Data item names `migrated to <where it went>` or
`archived at <where it is>`, the one that happened, and the User notice's fenced draft is
replaced by the text actually sent, with its groups and dates. The check below refuses a
`done` section still holding one. A section not confirmed stays `Status: pending`, its items
as they were.

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/retire-system/scripts/retire_check.py" record --file {{retirements_dir}}/<name>.md --config "<project root>/.claude/project.json" --today <today>
```

An `INVALID:` line is a record this skill wrote wrong: fix that line and run it again.
**While it prints `pending: <sections>`, stop here and commit nothing**: the record stays
uncommitted in the working tree, and a re-run continues from it. Report the path and the
sections still pending.

## Step 5 — Commit the record

Only when the check prints `done`. Since Step 4's wait may have been long, repeat Step 1's
first stop, then run `git fetch origin` again; if `origin/retire/<name>` now exists, or
`git cat-file -e origin/{{parent_branch_default}}:{{retirements_dir}}/<name>.md` succeeds,
stop and ask, as Step 1 does. Then cut the branch from the freshly fetched parent and commit the
record alone:

```bash
git switch -c retire/<name> origin/{{parent_branch_default}}
git add {{retirements_dir}}/<name>.md
```

Before the commit, unless `{{secret_scan_command}}` is `none`, scan what is staged, as
`gates/definition-of-done.md` step 7 scans every commit:

```bash
(
  gate="${CLAUDE_PLUGIN_ROOT}/gates/scripts/sarif_gate.py"; patch=$(mktemp)
  secrets_sarif=$(mktemp); trap 'rm -f "$patch" "$secrets_sarif"' EXIT
  python3 "$gate" patch --staged > "$patch" || exit 2
  ( {{secret_scan_command}} ) < "$patch" > "$secrets_sarif"
  python3 "$gate" secrets "$secrets_sarif"
)
```

Anything but `clean` stops the skill before the commit: report each `rule file:line` it
printed, never the text, and rewrite those lines to name the credential rather than hold it.
A re-run finishes the commit as Step 1 describes, scanning again. Then:

```bash
git commit -m "Record the retirement of <name>" -- {{retirements_dir}}/<name>.md
```

A failed switch or commit stops the skill with the file in place; a re-run continues from
it, finishing the commit as Step 1 describes. Do not push. Report the path and the commit,
and say that HEAD is left on `retire/<name>`, to be switched back from when the record is
pushed.
