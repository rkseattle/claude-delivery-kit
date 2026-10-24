---
name: release
description: Run the rule book's Phase 6 for a version that passed release-readiness — tag, build the artifact once, write release notes, test the rollback in staging, roll out stage by stage on the release manager's approval while watching the halt criteria, roll back first on a halt, publish the notes, and move the released tickets on.
argument-hint: <version, e.g. 1.4.0>
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Release: $ARGUMENTS

This skill is the rule book's Phase 6 in its order: build once from a tag, write the notes,
prove the rollback in staging, roll out in stages under halt criteria set beforehand, roll
back first when one fires, then publish and update the tickets. Its exit criteria are
`${CLAUDE_PLUGIN_ROOT}/gates/release.md`; read that file in Step 1, before the tag.

Nothing leaves this checkout before `{{roles.release_manager}}` approves it. The tag is
created locally in Step 3 and pushed only in Step 6. Any exit before that push deletes it
with `git tag -d v<version>` and says so, so the same version can be released again once
the cause is fixed. A fix that moves HEAD needs a new `release-readiness` run first. The
two exceptions: once the last stage's window closes clean, or once any rollback has failed,
the tag is never deleted. Production then runs the tagged artifact, and recovery needs the
tag.

## Step 1 — Read the configuration and check the prerequisites

**Every configured command runs in a subshell from the project root** —
`( {{command}} <arguments> )`, with any redirect outside the parentheses — so a `cd` or
`export` inside it cannot move or change the shell for the commands after it, as
`gates/definition-of-done.md` runs `{{sast_command}}`. This holds for each command below,
written in a code block or named in prose.

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly, then
`${CLAUDE_PLUGIN_ROOT}/gates/release.md`, whose stops come before the tag; this skill's
optional keys are `release_dir`, `release_artifact_command`, `deploy_command`,
`smoke_test_command`, `rollback_command`, `rollout_stages`, `halt_criteria`,
`monitoring_window_minutes`, `released_status`, `project_size`, `roles`, and `disciplines`,
with the keys its named disciplines need here: `security_sensitive_paths`,
`api_compat_command`, `min_supported_app_version`, and `error_budget_command`. A key no named
discipline needs is not used, so it is not announced.

Every stop below comes before the tag, and says why in one line.

- **The `release_dir` check prints anything but `ok`.** It runs first, since the commands
  after it write the path unquoted.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" release-dir --value "{{release_dir}}"
  ```

- **`{{deploy_command}}` or `{{rollback_command}}` is `none`** — name the key. A release
  with no automated deploy is not repeatable, and one with no rollback is not reversible:
  the Phase 6 policy is unmet before anything starts.
- **Any other stop `gates/release.md` lists before the tag** — a `none` artifact, smoke, or
  `release_dir` key, or any non-zero exit from the tested check of `halt_criteria`,
  `monitoring_window_minutes`, and `rollout_stages`, whose `INVALID:` line names the key:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release/scripts/halt_watch.py" --check --config "<project root>/.claude/project.json"
  ```

  Write the project root as its absolute path: `CLAUDE_PROJECT_DIR` is not set in the
  session's shell. Each would let a criterion pass with nothing checked. With `mobile` in
  `{{disciplines}}`, it also stops on fewer than two `rollout_stages`.
- **The discipline check prints anything but `ok`.** Name each `INVALID:` line:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" disciplines --config "<project root>/.claude/project.json" --gate release
  ```

- **`$ARGUMENTS` is not `MAJOR.MINOR.PATCH`**: this prints anything but `ok`.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" version --new <version>
  ```
- **The readiness record does not hold**: the tested check below prints anything but `ok`.
  It requires the summary to exist, to end `Gate: PASS` with the `Reviewed-by:` line
  `gates/release-readiness.md` criterion 4 defines directly before it, and to match, as it
  is now, the note `release-readiness` wrote on HEAD. A `Reviewed-by:` line anywhere else
  may be text the summary quoted from a PR, and a summary edited since the review no longer
  matches its note. Name what it printed, and send it back to
  `release-readiness <version>`.

  ```bash
  git notes --ref=release-readiness show HEAD |
    python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" verify --summary {{release_dir}}/<version>-test-summary.md --version v<version> --require-pass
  ```
- **HEAD is not on `origin/{{parent_branch_default}}`.** After `git fetch origin`,
  `git merge-base --is-ancestor HEAD origin/{{parent_branch_default}}` must exit 0. A release
  is cut from the reviewed mainline, as trunk-based release practice and Humble and Farley's
  build-once-from-the-mainline both require; a feature branch or an unpushed local commit
  was never merged through review.
- **`git status --porcelain --untracked-files=all -- . ':(exclude){{release_dir}}'` prints
  anything.** The deploy, smoke, rollback, and halt commands run from this checkout, so an
  untracked or modified file there would produce evidence for a tree nobody recorded.
- **The summary's `Commit:` is not HEAD**, by the tested check. Record that SHA: it is the
  `<verified SHA>` Step 3 tags, so a HEAD that moves during a later wait is never tagged:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" commit --summary {{release_dir}}/<version>-test-summary.md --head "$(git rev-parse HEAD)"
  ```
- **`v<version>` already exists**, locally (`git rev-parse -q --verify refs/tags/v<version>`
  prints a SHA) or on origin (`git ls-remote --exit-code --tags origin refs/tags/v<version>`
  exits 0). Any exit status other than 0 or 2 from `ls-remote` is a failed lookup, named as
  that, not as an absent tag. A tag only local is one an interrupted run left, and that run
  may have deployed a production stage that now runs it unmonitored: ask
  `{{roles.release_manager}}` whether any stage was deployed before suggesting
  `git tag -d v<version>`.

- **With `mobile`, the API check below exits non-zero**, run from the project root last,
  once the checkout is known clean and on the mainline: the server API no longer serves the
  oldest app version still supported, and a shipped binary cannot be recalled to match it.

  ```bash
  ( {{api_compat_command}} {{min_supported_app_version}} )
  ```

**The stages.** `{{rollout_stages}}` is a list of production stage names, in order, each
passed to the commands as `<stage>`. With `mobile`, they are the store's phased release, a
partial phase before the full one, and `none` has already stopped above. Otherwise, with it
`none`:

- A `{{project_size}}` of `small` gets one stage, `production` — the rule book's
  "Tailoring and exceptions" makes staged rollout optional at that size.
- A `medium` or `large` project stops and asks `{{roles.release_manager}}`, printed per
  `gates/project-config.md`, either to set `rollout_stages` and run this skill again, or to
  approve one `production` stage for this release. Only an explicit approval continues, and
  it continues with that one stage.

## Step 2 — The scope

Compute the release scope exactly as `release-readiness` Step 2 does, and print the range
and keys as literal values, now, before the tag exists. After Step 3, `git describe` would
return the new tag and the scope would be empty. A range or key list that differs from the
summary's `Scope:` line stops the release: a tag fetched since, or a commit, changed what
would be released from what was tested. The tested check decides it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" scope --summary {{release_dir}}/<version>-test-summary.md --range <range> --keys <KEY>,<KEY>
```

Reuse this list of keys and this range for the rest of the run. Then, still before the tag,
the discipline stops that need them, each only when `{{disciplines}}` names it:

- **`sre`** — run the budget command, then the check, judging each on its own. Anything but
  `budget exited 0` stops the release; so does an `INVALID:` line from the check:

  ```bash
  mkdir -p {{release_dir}} && ( {{error_budget_command}} ) > {{release_dir}}/<version>-error-budget.txt; echo "budget exited $?"
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" error-budget < {{release_dir}}/<version>-error-budget.txt
  ```

  `ok <n>`, exit 0, continues. `spent <n>`, exit 1, is not yet a stop: read each scope key
  with `jira_get_issue` for its `labels`, and continue only when every one carries
  `reliability`. Otherwise stop, naming each key without it and each read that failed, which
  counts as unlabeled.
- **`security`** — list the sensitive paths the range changed:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" sensitive-paths --config "<project root>/.claude/project.json" --range <range>
  ```

  An `INVALID:` line stops the release. No path printed: continue, asking nothing. Otherwise
  write the paths to `{{release_dir}}/<version>-security-signoff.md`, one per line, creating
  the directory if needed, and ask
  `{{roles.security}}`, printed per `gates/project-config.md`, to sign off on them; then
  stop and wait. Only an explicit sign-off continues, recorded as that file's last line,
  `Signed-off-by: security <name> <YYYY-MM-DD>` with today's date from `date +%F`, and
  `, relayed by <git user.name>` after it for a relayed answer. Only the security role's
  answer counts. A clarifying question keeps the wait open; a refusal stops the release.

## Step 3 — Tag, then build once

Build in a fresh worktree of the tag, removed by a trap on every exit, as the pre-push
checklist's clean build does. Write `{{release_artifact_command}}`, `{{release_dir}}`, and
the version in full: shell variables do not survive between commands.

Run `git rev-parse HEAD` first: anything but Step 1's `<verified SHA>` means HEAD moved during
a wait since, and stops the release before the tag. Then:

```bash
git tag -a v<version> -m "Release v<version>" <verified SHA>
git worktree prune
mkdir -p {{release_dir}}
repo=$PWD; out="$repo/{{release_dir}}"
build=$(mktemp -d) && git worktree add --detach "$build" v<version> && (
  set -o pipefail
  trap 'cd "$repo" && git worktree remove --force "$build"' EXIT
  cd "$build" && ( {{release_artifact_command}} ) | tee "$out/<version>-build.log" &&
    artifact=$(tail -n 1 "$out/<version>-build.log") && [ -f "$artifact" ] &&
    cp "$artifact" "$out/<version>-$(basename "$artifact")" &&
    python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" hash "$out/<version>-$(basename "$artifact")" > "$out/<version>-artifact.sha256"
); build_status=$?
rmdir "$build" 2>/dev/null; echo "build exited $build_status"
```

The build reads the tagged commit and nothing else in this checkout. Its last line of
standard output is the artifact's path, relative to the worktree unless absolute. Any exit
but `build exited 0` stops the release. The copy in `{{release_dir}}` is `<artifact-path>`,
written out as an absolute path from here on, and in double quotes wherever a command takes
it, since the build chose its file name; it outlives the worktree, so the artifact
production runs is never lost with it. Its SHA-256 is recorded beside it, and before every
deploy, staging's and each production stage's, this check runs; a mismatch stops the
release before staging and is a halt after it, since a changed file is not the artifact
that was tested:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" artifact --path "<artifact-path>" --sha256-file {{release_dir}}/<version>-artifact.sha256
```

The build command never runs again in this release — a rebuild is a different artifact
than the one about to be tested.

## Step 4 — Write the release notes

Write `{{release_dir}}/<version>-notes.md` from what this checkout already holds, so
nothing between here and the staging ask needs the network:

```markdown
# v<version>

## Changes
## Migrations
## Known issues
## Rollback
## Remote flags
```

- **Changes** — one line per scope key, with each commit subject in the range that names
  it. A subject names the keys Step 2's `grep -oE … | grep -xE …` pipeline takes from it,
  so a key never takes the subjects of a longer key it begins.
- **Migrations** — the summary's `Upgrade notes` section, or `none`.
- **Known issues** — the open Bugs under the summary's `Open defects by severity` whose
  keys are in the scope, then its `Known risks`. The summary's defect list is project-wide,
  for the gate; the published notes name only this release's tickets.
- **Rollback** — `{{rollback_command}} <stage>` for each production stage, newest first.
- **Remote flags**, with `mobile` only, the heading left out otherwise — one
  `- <KEY>: <flag>` line per scope key, naming every flag a `Remote-flag:` git trailer gives
  on the range's commits whose subject names the key, as Changes reads it, comma-separated.
  This prints each commit's subject, then its flags on a line of their own, empty when it
  has none:
  `git log --format='%s%nRemote-flag: %(trailers:key=Remote-flag,valueonly,separator=%x2C)' <range>`.
  For each key with no trailer, ask `{{roles.release_manager}}`, printed per
  `gates/project-config.md`, in one question listing them all, for the flag that gates its
  new behavior or the reason none does, and wait. Only the release manager's answer counts,
  printed as relayed when it is; write each as given, `- <KEY>: <flag>` or
  `- <KEY>: none — <reason>`. Nothing is filled in for them.

Then check the file: anything but `ok` stops the release here, per `gates/release.md`
criterion 1. With `mobile`, run the second line instead, with Step 2's keys:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" notes-headings --notes {{release_dir}}/<version>-notes.md
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py" notes-headings --notes {{release_dir}}/<version>-notes.md --flag-keys <KEY>,<KEY>
```

## Step 5 — Staging, then each production stage

**The staging ask.** Ask `{{roles.release_manager}}` once, printed per
`gates/project-config.md`. The question names:

- the artifact path;
- `{{deploy_command}} staging "<artifact-path>"`, then `{{smoke_test_command}} staging`, then
  `{{rollback_command}} staging`, then `{{smoke_test_command}} staging` again;
- the rollback of staging that any failure triggers;
- the release notes, in full, since Step 6 publishes them;
- with `embedded`, a request to confirm that the artifact installs atomically with a
  fallback image, A/B partitions or equivalent. An approval that does not confirm it keeps
  the wait open.

Then stop and wait. Run no `{{deploy_command}}` before an answer. A clarifying question is
not an answer, and only the release manager's answer counts; one relayed by the person
running the session is printed as relayed.

On approval, run Step 3's artifact check, then the four commands in that order from the
project root. A failure stops the
release: if staging was deployed and not yet rolled back, run `{{rollback_command}} staging`
first, then report which command failed. A failed `{{deploy_command}} staging` counts as
deployed, since it may have changed staging part-way. A failed rollback is reported as
staging left on the new artifact, and the tag stays, named in the report. Nothing reaches
production. A pass settles `gates/release.md` criterion 1.

**Each production stage**, in order — the first one too, never only the later ones. Every
command from here to the end of Step 6 runs from the project root, never the build worktree:

1. Ask `{{roles.release_manager}}` to approve `<stage>`. The approval covers that stage's
   deploy, its smoke test, its monitoring window, and its rollback on a halt, with no
   further ask. The last stage's question also names the tag push, the notes as they will be
   published, and the ticket transition of Step 6, which its approval covers too. Print the
   role per `gates/project-config.md`, then stop and wait as for staging: a clarifying
   question keeps the wait open. An explicit refusal or abort ends the rollout as a halt
   does, minus the halt itself: roll back every production stage already deployed, newest
   first, under their own approvals. That is Argo Rollouts' abort, which returns a rollout
   to its stable version, never one left part-way.
2. With `sre`, Step 2's budget check again, since the approvals since may have taken long:
   a spent budget with any scope ticket not labeled `reliability`, or a failed read, refuses
   this stage, and the rollout ends as item 1's abort does. With `mobile`, before the first
   production stage only, Step 1's API check again, a non-zero exit refusing it the same way.
   Then Step 3's artifact check, then `{{deploy_command}} <stage> "<artifact-path>"`, then
   `{{smoke_test_command}} <stage>`.
3. Watch the halt criteria for the window with the command below. Run it as one background
   command and wait for it to finish. It keeps no state the session must poll, and nothing
   else runs meanwhile.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/release/scripts/halt_watch.py" --config "<project root>/.claude/project.json"
```

`${CLAUDE_PLUGIN_ROOT}` is filled in when this skill loads. Write the project root's
absolute path in full: other shell variables, `CLAUDE_PROJECT_DIR` among them, are not set
in the session's shell, and the script runs each criterion from that root. The script reads
`{{halt_criteria}}` and `{{monitoring_window_minutes}}` itself, so no command's quoting
passes through this session. Each round starts on the minute, from minute 0 through the
window's end, and runs every criterion at once. A criterion fires when it exits non-zero or
has not exited 55 seconds into its round, and a value the script cannot read is a halt too.
Only an exit of 0 with a last line of `window clean` settles `gates/release.md` criterion 3.
Any other ending is a halt: a `HALT` line, a traceback, a missing `python3`, a killed or
interrupted task.

**On a halt — a fired criterion, a watch that did not end clean, a failed artifact check
before a production stage, a failed production deploy, or a failed production smoke test —
roll back first.** Before reading logs, reporting, or anything else, run
`{{rollback_command}} <stage>` for every production stage deployed, newest first: the failed
one included when its deploy ran, as after a failed deploy, smoke test, or watch, and left
out when its artifact check failed, since that stage was never deployed and still runs the
previous release. Each stage's own approval already authorized its rollback. Then report the
criterion or smoke output, each rollback's result, and the stage the release stopped at.
Delete the local tag and stop, unless a rollback failed: then production still runs the
tagged artifact, so the tag stays and is named in the report. A rollback that itself fails
does not stop the older stages' rollbacks, and is reported first, in one line, as the
emergency it is.

## Step 6 — Publish and update the tickets

Once the last stage's window closes clean, production runs the release, so every command
below runs in order and the first to fail stops the rest of this block. Git does not fetch
notes by default, so first merge origin's readiness notes into the local ref, when origin
has one, keeping the local note for any commit both hold; `ls-remote` exit 2 means absent,
as in Step 1:

```bash
git ls-remote --exit-code origin refs/notes/release-readiness >/dev/null
case $? in
  0) git fetch -q origin +refs/notes/release-readiness:refs/notes/remote/release-readiness &&
       git notes --ref=release-readiness merge -q -s ours refs/notes/remote/release-readiness &&
       git update-ref -d refs/notes/remote/release-readiness ;;
  2) true ;;
  *) false ;;
esac
```

```bash
git push --atomic origin v<version> refs/notes/release-readiness
gh release create v<version> --verify-tag --title v<version> \
  --notes-file {{release_dir}}/<version>-notes.md
gh release view v<version> --json isDraft --jq .isDraft
```

The tag and the notes ref go in one `--atomic` push, so the review record reaches the remote
with the commit it attests, or neither does. `--verify-tag` refuses to create a tag GitHub
does not have, so the release cannot point at a different commit. Criterion 4 needs
`create` to exit zero in this run and the view to print `false`. A failure in either block
does not roll back production: report the command that failed and every command from it
to the end of the block, in order, as the steps still to run. The ticket transitions below
run either way, since the tickets were released when production took the artifact.

Then, unless `{{released_status}}` is `none`, move each scope ticket there. A ticket already
in that status is left alone. For each other key, use `jira_get_transitions`, then the
transition whose target status, where the result names one, or else whose own name, equals
`{{released_status}}` exactly, by its ID — never a guessed one. Then read the issue back and
confirm its status name is `{{released_status}}`. Report by key any ticket with no such
transition, with the names it does offer, or not in that status afterward, and leave it to
`{{roles.release_manager}}`. With `{{released_status}}` `none`, move nothing; Step 1's
announcement already named it.

Report each criterion of `gates/release.md` and how it stands, each `Discipline addenda`
section that applied and what settled it, the tag, the release URL, and the tickets moved.
