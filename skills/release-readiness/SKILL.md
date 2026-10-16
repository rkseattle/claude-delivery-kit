---
name: release-readiness
description: Run the rule book's Phase 5 release gate for a version — system, integration, and non-functional suites over every ticket committed since the last release tag, open defects by severity, Must tickets not done, and each merged PR's risks — write the test summary with a PASS or FAIL verdict, and stop for the product owner's review.
argument-hint: <version, e.g. 1.4.0>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Check release readiness for: $ARGUMENTS

This skill is the rule book's Phase 5 step 7 and its exit gate: it writes the test summary
for one release candidate and stops for `{{roles.product_owner}}`. It writes one file,
`{{release_dir}}/<version>-test-summary.md`, and nothing else. No commit, tag, or push:
`release` reads the file from the working tree, and a commit after it would move HEAD off
the commit the summary tested.

## Step 1 — Read the configuration

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's
optional keys are `system_test_command`, `system_results_file`,
`system_results_read_command`, `integration_test_command`, `integration_results_file`,
`integration_results_read_command`, `nfr_test_command`, `release_dir`, `exceptions_log`,
and `roles`. Then read `${CLAUDE_PLUGIN_ROOT}/gates/release-readiness.md`, which decides
the verdict.

Stop, and say why in one line, when:

- **`{{system_test_command}}` or `{{release_dir}}` is `none`** — absent or set so. Name the
  key: with no system suite there is no Phase 5 system level to report, and with no release
  directory the summary has nowhere to live.
- **Any other stop `gates/release-readiness.md` names before a suite runs** — a `none`
  system results file or reader, or a system results file shared with another suite.
- **`{{integration_test_command}}` is set, and `{{integration_results_file}}` or
  `{{integration_results_read_command}}` is `none`, or `{{integration_results_file}}` equals
  `{{results_file}}`** — `gates/pre-push.md` step 6's stop, for the same reason.
- **`$ARGUMENTS` is not `MAJOR.MINOR.PATCH`**, three dot-separated non-negative integers
  with no leading `v` — Semantic Versioning's core form. The tag `release` creates is
  `v<version>`, so a leading `v` would double it.
- **`git status --porcelain --untracked-files=no -- . ':(exclude){{release_dir}}'` prints
  anything.** The suites run against the working tree, and the summary records HEAD: a
  tracked change would be tested and not recorded. Untracked files do not count, and
  neither does `{{release_dir}}`, which this kit writes to and never commits.

With `{{integration_test_command}}` `none`, the one line `gates/project-config.md` defines
says the project has no integration tier. With `{{nfr_test_command}}` `none`, it says every
in-scope NFR counts as failed, per the gate's criterion 3.

## Step 2 — The release scope

The scope is every `{{ticket_prefix}}` key named in a commit subject since the last
release. The last release is the nearest `v*` tag reachable from HEAD, which is what
`git describe` returns; with none, the range is all of history back to the root commit:

```bash
last=$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null) && range="$last..HEAD" || range=HEAD
git log --format=%s "$range" | grep -oE '[A-Z][A-Z0-9_]*-[0-9]+' | grep -xE '{{ticket_prefix}}-[0-9]+' | sort -u
```

Subjects only, because the subject names the ticket a commit delivers, by the convention
every stage of this kit commits with. A body names tickets for other reasons, such as work
left to a later ticket, and history cannot be rewritten once merged, so one such mention
would fail every release cut from it. The first `grep` takes whole keys, so a longer prefix
ending in `{{ticket_prefix}}` never counts as one of this project's. Record the range,
the keys, and `git rev-parse HEAD`, and print the tag and range as literal values: shell
variables do not survive between commands, so every later step writes them out in full. An
empty scope stops the skill: there is nothing to release.

## Step 3 — Run the suites

Run the suites in this order. Delete the system and integration results files before their
suites run, so a crashed run cannot leave the previous verdict to be read as this one's:

1. **System** — `{{system_test_command}}`; record its exit status, then read passed,
   failed, and executed from `{{system_results_file}}` with
   `{{system_results_read_command}}`. When Step 2 found a tag `v<last>` and
   `{{release_dir}}/<last>-test-summary.md` exists, compare the executed count against
   its system row.
2. **Integration** — `{{integration_test_command}}`, unless `none`; record its exit status,
   then read `{{integration_results_file}}` with `{{integration_results_read_command}}`. A
   non-zero exit, a failed test, a results file missing or unreadable afterward, or an
   executed count of zero is a failing integration run. Its row says which, and so does
   `Known risks`.
3. **Non-functional** — `{{nfr_test_command}}`, unless `none`, run with no arguments. It
   prints one line per NFR, `<KEY> NFR<n> pass` or `<KEY> NFR<n> fail`. Keep every line,
   and settle each in-scope NFR from them as the gate's criterion 3 says. A line in any
   other form is listed under `Known risks` as unreadable, never guessed at.

Read counts from the results files, never from the console or an exit code. An executed
count of zero is a run that died early, not a pass.

## Step 4 — Jira and the merged PRs

Read Jira through the Atlassian MCP. A call that errors or stops short is a failed read,
and fails the gate criteria that depend on it. It is named in the summary under
`Gate criteria`, and never written as an empty section.

- **The scope's tickets** — read each key on its own with `jira_get_issue`, for `summary`,
  `status`, `labels`, `issuetype`, `parent`, and `description`. One key at a time, because
  Jira rejects a whole `key in (…)` search over one key it does not know.
  `jira_get_issue` also returns the description in Markdown, which `jira_search` strips of
  its headings and list markers, as `write-tickets` relies on when it reads tickets back.
  A key Jira reports as not found is handled as the gate says. Any other error is a failed
  read.
- **Must tickets not done** — of those, each with the `moscow-must` label whose status
  category is not `Done`.
- **In-scope NFRs** — as the gate's criterion 3 defines them. Reach a ticket's Epic by
  following `parent` with `jira_get_issue` until an issue of type Epic, or none.
- **Open defects** — `jira_search`, paging until every result is read, for
  `project = {{jira_project}} AND issuetype = Bug AND statusCategory != Done`, grouped by
  `severity-critical`, `severity-high`, `severity-medium`, and `severity-low`. An open Bug
  with none of them is grouped `Unrated`.

Then, for each key, find its merged PRs:

```bash
gh pr list --state merged --search '"<KEY>" in:title,body' --limit 1000 --json number,title,body,url,mergeCommit
```

A result count equal to the limit stops the skill as a `gh` error does, since more may
exist. GitHub's search tokenizes the key even when quoted. Keep only a PR whose title or
body contains the key as a whole word, and whose `mergeCommit.oid` is a commit in the range,
`git rev-list <range> | grep -qx <oid>`, with Step 2's literal range; a `git rev-list` that
fails stops the skill as a `gh` error does. A PR merged before the last release, whose body
merely names a scope key, is not this release's. Read each PR once even when several keys
find it. From each body, take the `Risks` section, and the section whose heading names
migrations or upgrade notes. A section runs from its heading — a Markdown heading, or a bold
lead-in such as `**Risks**` — to the next one. A PR with no `Risks` section is listed as
having none, which is not the same as risks of `none`. A `gh` error stops the skill, named
as that: a risk list missing because GitHub was unreachable would read as a release with no
risks.

## Step 5 — Write the summary

Apply every criterion in `gates/release-readiness.md` to what Steps 3 and 4 read, then
write `{{release_dir}}/<version>-test-summary.md`, creating the directory if needed and
replacing any earlier summary for the same version whole. A re-run is a new verdict, and an
old `Reviewed-by:` line does not carry over to it.

```markdown
# Test summary — v<version>

Commit: <full SHA of HEAD>
Scope: <range> — <n> tickets: <KEY>, <KEY>, …

## Pass rate by level

| Level | Passed / executed | Failed |
| --- | --- | --- |
| system | <p> / <e> | <f> |
| integration | <p> / <e> | <f> |

## Non-functional results

| NFR | Result | Exception |
| --- | --- | --- |
| <KEY> NFR<n> | pass, fail, or no result | <the matching register row's Rule and Expiry, or none> |

## Open defects by severity

### Critical
### High
### Medium
### Low
### Unrated

## Must tickets not done

## Known risks

## Upgrade notes

## Gate criteria

<each exit criterion, and whether it holds, with the fact that settles it>

Gate: PASS
```

The integration row reads `not run — no integration tier` when
`{{integration_test_command}}` is `none`. A row whose suite left no counts to read reads
`no result — <exit status, or the file missing or unreadable>`, never `0 / 0`. A
Non-functional row lists each in-scope NFR.
Under a defect heading, each Bug is one line of key, summary, and status. An empty section
says `none`. `Known risks` lists each PR's `Risks` section under its number and title,
then the unreadable lines and scope keys Jira does not know, then a system executed count
below the previous release's.
`Upgrade notes` lists each PR's migration section the same way, and `release` copies it
into its notes' `Migrations`. The last line is `Gate: PASS` or `Gate: FAIL`, per the gate's
verdict.

## Step 6 — Stop for the product owner

Present to `{{roles.product_owner}}`, printed per `gates/project-config.md`:

- the summary's path and the `Gate:` verdict
- each exit criterion and how it stands, with "Test summary reviewed by product owner"
  open
- every failing criterion's facts, one line each

Then stop and wait. An explicit "reviewed", "approved", or equivalent records the review. A
clarifying question is not an answer, and neither is a request for changes. Fixing a
failing test, closing a defect, or recording an exception happens outside this skill, and
a re-run writes a fresh summary. Only the product owner's answer counts, and one relayed by
the person running the session is printed as relayed. A `Gate: FAIL` summary is reviewed
the same way, per the gate's criterion 4.

## Step 7 — Record the review

On the product owner's answer, insert one line directly before the `Gate:` line, with
today's date from `date +%F` — a git-style trailer, the form `git interpret-trailers`
parses:

```text
Reviewed-by: product_owner <name> <YYYY-MM-DD>
```

`<name>` is the person who answered: the product owner as `roles` names them, or with no
product owner in `roles`, the person running the session by git `user.name`, never the
word "you". A relayed answer, as `gates/project-config.md` defines one, names the person
the session said it came from and appends `, relayed by <git user.name>` after the date.
Then report the path and the verdict, and name `release <version>` as the next step only when the verdict is
`Gate: PASS`.
