---
name: release-readiness
description: Run the rule book's Phase 5 release gate for a version — system, integration, and non-functional suites over every ticket committed since the last release tag, open defects by severity, Must tickets not done and their untested acceptance criteria, and each merged PR's risks — write the test summary with a PASS or FAIL verdict, and stop for the product owner's review.
argument-hint: <version, e.g. 1.4.0>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Check release readiness for: $ARGUMENTS

This skill is the rule book's Phase 5 step 7 and its exit gate: it writes the test summary
for one release candidate and stops for `{{roles.product_owner}}`. In `{{release_dir}}` it
writes `<version>-test-summary.md` and its `<version>-note.txt`, a `<version>-<KEY>.md` copy
of each scope ticket's and Epic's description it reads, the `<version>-nfr-output.txt` and
`<version>-nfrs.txt` the NFR check reads, and with `data-ml`, the
`<version>-model-thresholds.txt` its model command reads. After the review it adds a git
note on the tested commit under `refs/notes/release-readiness`. No commit to any branch, no
tag, and no push: a note does not move HEAD, and `release` reads both the file from the
working tree and the note, then pushes the note with the tag.

## Step 1 — Read the configuration

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it. Read
`${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly; this skill's optional
keys are `system_test_command`, `system_results_file`, `system_results_read_command`,
`integration_test_command`, `integration_results_file`, `integration_results_read_command`,
`nfr_test_command`, `release_dir`, `exceptions_log`, `results_file`, `roles`, and
`disciplines`, with the keys its named disciplines need here: `data_quality_command`,
`model_eval_command`, `model_eval_thresholds`, `device_matrix`, `device_test_command`, and
`hil_test_command`. A key no named discipline needs is not used, so it is not announced.
Then read `${CLAUDE_PLUGIN_ROOT}/gates/release-readiness.md`, which decides the verdict.

Stop, and say why in one line, when:

- **`{{system_test_command}}` or `{{release_dir}}` is `none`** — absent or set so. Name the
  key: with no system suite there is no Phase 5 system level to report, and with no release
  directory the summary has nowhere to live.
- **Any other stop `gates/release-readiness.md` names before a suite runs** — a `none`
  system results file or reader, or a system results file shared with another suite.
- **The discipline check prints anything but `ok`.** Name each `INVALID:` line:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" disciplines --config "<project root>/.claude/project.json" --gate readiness
  ```
- **`{{integration_test_command}}` is set, and `{{integration_results_file}}` or
  `{{integration_results_read_command}}` is `none`, or `{{integration_results_file}}` equals
  `{{results_file}}`** — `gates/pre-push.md` step 6's stop, for the same reason.
- **`$ARGUMENTS` is not `MAJOR.MINOR.PATCH`**, three dot-separated non-negative integers
  with no leading `v` — Semantic Versioning's core form — as Step 2's version check
  decides. The tag `release` creates is `v<version>`, so a leading `v` would double it.
- **HEAD is not on `origin/{{parent_branch_default}}`.** After `git fetch origin`,
  `git merge-base --is-ancestor HEAD origin/{{parent_branch_default}}` must exit 0. A release
  is cut from the reviewed mainline, as trunk-based release practice and Humble and Farley's
  build-once-from-the-mainline both require; a feature branch or an unpushed local commit
  was never merged through review.
- **`git status --porcelain --untracked-files=all -- . ':(exclude){{release_dir}}'` prints
  anything, or the `release_dir` check below prints anything but `ok`.** `release_dir` must
  be relative, inside the repository, and free of whitespace: the commands below write it
  unquoted and relative to the project root.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" release-dir --value "{{release_dir}}"
  ```

  The suites run against the working tree, and the summary records HEAD: a modified or
  untracked file, a fixture or a config the suites pick up, would be tested and not
  recorded. Ignored files and `{{release_dir}}`, which this kit
  writes to and never commits, do not count.

With `{{integration_test_command}}` `none`, the one line `gates/project-config.md` defines
says the project has no integration tier. With `{{nfr_test_command}}` `none`, it says every
in-scope NFR counts as failed, per the gate's criterion 3.

## Step 2 — The release scope

The scope is every `{{ticket_prefix}}` key named in a commit subject since the last
release. The last release is the nearest `v*` tag reachable from HEAD, which is what
`git describe` returns; with none, the range is all of history back to the root commit.
History must be whole first: `git rev-parse --is-shallow-repository` printing `true` stops
the skill, since a shallow clone hides both tags and commits. `git describe` failing for
any reason but finding no tag, its `No names found` or `No tags can describe`, stops it
too, rather than reading as a first release:

```bash
{ last=$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' --exclude 'v*-*' 2>&1) && range="$last..HEAD" ||
  case $last in *"No names found"*|*"No tags can describe"*) range=HEAD ;; *) echo "$last"; false ;; esac; } &&
  git log --format=%s "$range" | python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" ticket-keys --prefix "{{ticket_prefix}}"
```

Then check the version, passing `--last` only when the command above found a tag. Only a
full `vMAJOR.MINOR.PATCH` tag counts as a release: a pre-release such as `v1.2.0-rc1` is
excluded from the search, so it neither starts the range nor blocks the next version.
Anything but `ok` stops the skill: a malformed version, or one not greater than the last in
Semantic Versioning precedence, would mislabel history.

The version, from `$ARGUMENTS`, is handed over as a file per **Untrusted text** in
`gates/project-config.md`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" version --last v<last> < "<version file>"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" version < "<version file>"
```

The first line is for a release after a tag, the second for the first release.

Subjects only, because the subject names the ticket a commit delivers, by the convention
every stage of this kit commits with. A body names tickets for other reasons, such as work
left to a later ticket, and history cannot be rewritten once merged, so one such mention
would fail every release cut from it. The first `grep` takes whole keys, so a longer prefix
ending in `{{ticket_prefix}}` never counts as one of this project's. Record the range,
the keys, and `git rev-parse HEAD`, and print the tag and range as literal values: shell
variables do not survive between commands, so every later step writes them out in full. An
empty scope stops the skill: there is nothing to release.

## Step 3 — Run the suites

**Every configured command runs in a subshell from the project root** —
`( {{command}} <arguments> )`, with any redirect outside the parentheses — so a `cd` or
`export` inside it cannot move or change the shell for the commands after it, as
`gates/definition-of-done.md` runs `{{sast_command}}`. This holds for each command below,
written in a code block or named in prose.

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
3. **Non-functional** — create the directory and empty the output file, so no earlier
   run's lines are read as this one's, then, unless `{{nfr_test_command}}` is `none`, run
   it with no arguments. It prints one line per NFR, `<KEY> NFR<n> pass` or
   `<KEY> NFR<n> fail`; Step 4 settles them. With the command `none`, run only the first
   line, and the file stays empty, so every in-scope NFR has no result.

   ```bash
   mkdir -p {{release_dir}} && : > {{release_dir}}/<version>-nfr-output.txt
   ( {{nfr_test_command}} ) >> {{release_dir}}/<version>-nfr-output.txt
   ```

4. **Discipline addenda** — only for each discipline `{{disciplines}}` names, as the gate's
   `Discipline addenda` define them, recording each command's exit status. With the project
   root written as its absolute path:

   ```bash
   ( {{data_quality_command}} )
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" thresholds --config "<project root>/.claude/project.json" > {{release_dir}}/<version>-model-thresholds.txt &&
     ( {{model_eval_command}} ) < {{release_dir}}/<version>-model-thresholds.txt
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" oldest-devices --config "<project root>/.claude/project.json"
   ( {{hil_test_command}} )
   ```

   The first two are `data-ml`'s; a `thresholds` failure is the model row's failure, its
   Command cell `thresholds` and its Result the `INVALID:` line, since the model never ran.
   The third prints `mobile`'s `<os> <version>` lines: run `{{device_test_command}} <os>
   <version>` once per line, in a subshell, each written out in full; its own failure is one
   failed `mobile` row. The last is `embedded`'s.

Read counts from the results files, never from the console or an exit code. An executed
count of zero is a run that died early, not a pass. The discipline commands report no
counts; their exit status is their result, as the gate defines it.

## Step 4 — Jira and the merged PRs

Read Jira through the Atlassian MCP. A call that errors or stops short is a failed read,
and fails the gate criteria that depend on it. It is named in the summary under
`Gate criteria`, and never written as an empty section.

- **The scope's tickets** — read each key on its own with `jira_get_issue`, for `summary`,
  `status`, `labels`, `issuetype`, `parent`, and `description`. One key at a time, because
  Jira rejects a whole `key in (…)` search over one key it does not know. `jira_get_issue`
  also returns the description in Markdown, which `jira_search` strips of its headings and
  list markers, as `write-tickets` relies on when it reads tickets back. A key Jira reports
  as not found is a failed read unless the register excepts it, as the gate says, checked
  with `python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py"
  excepted --rule "<KEY> not found" --exceptions {{exceptions_log}} --today "$(date +%F)"`.
  Only `ok`, exit 0, removes the key; a `MISMATCH:` or `INVALID:`, as with
  `{{exceptions_log}}` `none`, leaves it a failed read. Any other Jira error is a failed read.
- **Must tickets not done** — of those, each with the `moscow-must` label whose status
  category is not `Done`.
- **Must acceptance criteria** — as the gate's criterion 1 defines them, each with the tier
  and evidence of its tag, read by the tested check rather than by eye. Write each Must
  ticket's `jira_get_issue` description, verbatim, to `{{release_dir}}/<version>-<KEY>.md`
  with the Write tool, so no shell quoting touches it, then run, with the project root
  written as its absolute path:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" criteria --config "<project root>/.claude/project.json" < {{release_dir}}/<version>-<KEY>.md
  ```

  Each line is `<AC>`, `<tier>`, `<evidence>`, and `<status>`, separated by tabs, since
  evidence may hold spaces. A status other than `ok`, such as `no-criteria` or
  `unclosed-fence`, is a criterion 1 failure.
- **In-scope NFRs** — as the gate's criterion 3 defines them. Reach a ticket's Epic by
  following `parent` with `jira_get_issue` until an issue of type Epic, or none. Write each
  scope ticket's and Epic's description to `{{release_dir}}/<version>-<KEY>.md` with the
  Write tool, as for the Must criteria, then extract and settle them with the tested check,
  running the first `settle` line when `{{exceptions_log}}` is set and exists, and the
  second, with no register, otherwise. Empty the list
  first, with `: > {{release_dir}}/<version>-nfrs.txt`, then run `nfrs` once per key:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" nfrs --key <KEY> < {{release_dir}}/<version>-<KEY>.md >> {{release_dir}}/<version>-nfrs.txt
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" settle --nfrs-file {{release_dir}}/<version>-nfrs.txt --exceptions {{exceptions_log}} --today "$(date +%F)" < {{release_dir}}/<version>-nfr-output.txt
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" settle --nfrs-file {{release_dir}}/<version>-nfrs.txt --today "$(date +%F)" < {{release_dir}}/<version>-nfr-output.txt
  ```

  Each `settle` line is the NFR, `pass`, `excepted`, or `fail`, and why, separated by tabs;
  the `Non-functional results` table takes them as written. Lines naming NFRs outside the
  scope are ignored, as the gate says. An `INVALID:` line from either command — an NFR
  `nfrs` could not read, or a register `settle` could not — is a failed read, and fails
  criterion 3 named as that, never as an NFR result.
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
merely names a scope key, is not this release's. A scope key that no merged PR in the range
names is listed under `Known risks` as unreviewed: its commits reached the mainline without
a pull request. Read each PR once even when several keys find it. From each body, take the
`Risks` section, and the section whose heading names migrations or upgrade notes. A section
runs from its heading — a Markdown heading, or a bold lead-in such as `**Risks**` — to the
next one. A PR with no `Risks` section is listed as having none, which is not the same as
risks of `none`. A `gh` error stops the skill, named as that: a risk list missing because
GitHub was unreachable would read as a release with no risks.

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
| unit | not run here — the Definition of Done runs it before every commit | — |
| integration | <p> / <e> | <f> |
| system | <p> / <e> | <f> |
| acceptance | with the product owner — the review of `Untested requirements` | — |

## Untested requirements

| Requirement | Tier | Evidence |
| --- | --- | --- |
| <KEY> AC<n>, <KEY> NFR<n>, or <KEY> | <tier, `no tag`, or `no criteria`> | <the tag's evidence, or what is missing> |

## Non-functional results

| NFR | Result | Exception |
| --- | --- | --- |
| <KEY> NFR<n> | pass, excepted, or fail | <settle's reason, with the exception's expiry when excepted> |

## Open defects by severity

### Critical
### High
### Medium
### Low
### Unrated

## Must tickets not done

## Discipline checks

| Discipline | Command | Result |
| --- | --- | --- |
| <discipline> | <the command as run, with its arguments> | pass, or fail — exit <n> |

## Known risks

## Upgrade notes

## Gate criteria

<each exit criterion and each discipline section that applies, whether it holds, and the fact
that settles it>

Gate: PASS
```

The integration row reads `not run — no integration tier` when
`{{integration_test_command}}` is `none`. A row whose suite left no counts to read reads `no
result — <exit status, or the file missing or unreadable>`, never `0 / 0`. A Non-functional
row lists each in-scope NFR as `settle` printed it; one whose reason is `no result`, failed
or excepted, also appears under `Untested requirements`, as the gate says. `Untested
requirements` lists what the gate's criterion 1 says, a row per criterion or NFR with its
tier, or `no tag`: rule book Phase 5 step 7's untested requirements, the rows of a
traceability matrix no test covers. An NFR that ran and failed, or printed a line in another
form, belongs under `Non-functional results` only, as `settle` printed it: `fail`, or
`excepted` with its register row. Under a defect heading, each Bug is one line of key,
summary, and status. An empty section says `none`. `Known risks` lists each PR's `Risks`
section under its number and title, then the scope keys Jira does not know, then a system
executed count below the previous release's. `Upgrade notes` lists each PR's migration
section the same way, and `release` copies it into its notes' `Migrations`. The last line is
`Gate: PASS` or `Gate: FAIL`, per the gate's verdict. `Discipline checks` has one row per
discipline command run — `{{data_quality_command}}`, `{{model_eval_command}}`, each
`{{device_test_command}} <os> <version>`, and `{{hil_test_command}}`. A check script's
failure fills the row of the command it stopped, as Step 3 item 4 says, and adds none. The
section is left out whole when `{{disciplines}}` names none of
`data-ml`, `mobile`, and `embedded`.

## Step 6 — Stop for the product owner

Present to `{{roles.product_owner}}`, printed per `gates/project-config.md`:

- the summary's path and the `Gate:` verdict
- each exit criterion and how it stands, with "Test summary reviewed by product owner"
  open
- every failing criterion's or discipline section's facts, one line each
- `Untested requirements`, in full: the product owner's review is where those are
  accepted or sent back

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
product owner in `roles`, the person running the session by git `user.name`, never the word
"you". A relayed answer, as `gates/project-config.md` defines one, names the person the
session said it came from and appends `, relayed by <git user.name>` after the date. Then
record the verdict on the tested commit as a git note, so it stays with the SHA it attests
rather than only in a working file, as Gerrit's review-notes plugin records a change's
review in `refs/notes/review`. It is an integrity check, not a signed attestation:
anyone with the checkout can rewrite it, as anyone can the summary. What it adds is that the
summary `release` reads is the one that was reviewed. The note holds the version, the
summary's SHA-256, so a later edit to the file is detectable, and the summary's last two
lines, with trailing whitespace stripped, as `git notes` strips it. The tested check builds
it, and refuses a summary whose last two lines are not a review and a verdict:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" note --summary {{release_dir}}/<version>-test-summary.md --version v<version> > {{release_dir}}/<version>-note.txt &&
  test -s {{release_dir}}/<version>-note.txt &&
  git notes --ref=release-readiness add -f -F {{release_dir}}/<version>-note.txt <Commit SHA>
```

The note is written only from a note file the build produced: the check prints its
`INVALID:` line to standard error, and the chain stops at the first failure.

`-f` replaces a note an earlier run wrote for the same commit, and an empty file would
delete it. A non-zero exit from the build or the add stops the skill: name the command and
its output, and neither report the review as recorded nor name `release` as the next step,
since `release` would stop on the missing note. The note is local until `release` merges
origin's and pushes it with the tag. Otherwise report the path, the note, and the verdict,
and name `release <version>` as the next step only when the verdict is `Gate: PASS`.
