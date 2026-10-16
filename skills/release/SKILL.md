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

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: every `{{key}}` below comes from it.
Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` and follow it exactly, then
`${CLAUDE_PLUGIN_ROOT}/gates/release.md`, whose stops come before the tag; this skill's
optional keys are `release_dir`, `release_artifact_command`, `deploy_command`,
`smoke_test_command`, `rollback_command`, `rollout_stages`, `halt_criteria`,
`monitoring_window_minutes`, `released_status`, `project_size`, and `roles`.

Every stop below comes before the tag, and says why in one line:

- **`{{deploy_command}}` or `{{rollback_command}}` is `none`** — name the key. A release
  with no automated deploy is not repeatable, and one with no rollback is not reversible:
  the Phase 6 policy is unmet before anything starts.
- **Any other stop `gates/release.md` lists before the tag** — a `none` artifact, smoke, or
  `release_dir` key; a `halt_criteria` or `rollout_stages` that is not a JSON list of
  strings, is empty, or holds a blank entry or `staging`; a window that is not a positive
  whole number. Name the key: each would let a criterion pass with nothing checked.
- **`$ARGUMENTS` is not `MAJOR.MINOR.PATCH`**, as `release-readiness` requires.
- **`{{release_dir}}/<version>-test-summary.md` is missing, has no line starting
  `Reviewed-by:`, or its last line is not `Gate: PASS`.** Name which, and send it back to
  `release-readiness <version>`.
- **The summary's `Commit:` is not `git rev-parse HEAD`.** The summary tested another
  commit; name both SHAs.
- **`v<version>` already exists**, locally (`git rev-parse -q --verify refs/tags/v<version>`
  prints a SHA) or on origin (`git ls-remote --exit-code --tags origin refs/tags/v<version>`
  exits 0). Any exit status other than 0 or 2 from `ls-remote` is a failed lookup, named as
  that, not as an absent tag. A tag only local is one an interrupted run left: say so, and
  that `git tag -d v<version>` clears it.

**The stages.** `{{rollout_stages}}` is a list of production stage names, in order, each
passed to the commands as `<stage>`. With it `none`:

- A `{{project_size}}` of `small` gets one stage, `production` — the rule book's
  "Tailoring and exceptions" makes staged rollout optional at that size.
- A `medium` or `large` project stops and asks `{{roles.release_manager}}`, printed per
  `gates/project-config.md`, either to set `rollout_stages` and run this skill again, or to
  approve one `production` stage for this release. Only an explicit approval continues, and
  it continues with that one stage.

## Step 2 — The scope

Compute the release scope exactly as `release-readiness` Step 2 does, and print the range
and keys as literal values, now, before the tag exists. After Step 3, `git describe` would
return the new tag and the scope would be empty. Reuse this list of keys and this range for
the rest of the run.

## Step 3 — Tag, then build once

```bash
git tag -a v<version> -m "Release v<version>"
git worktree prune
build=$(mktemp -d) && git worktree add --detach "$build" v<version> && echo "$build"
```

Print the worktree's path, and from here on write it out in full: shell variables do not
survive between commands. Run `{{release_artifact_command}}` once, from that worktree. The
build reads the tagged commit and nothing else in this checkout, so untracked files never
reach the artifact. Its last line of standard output is the artifact's path, relative to the
worktree unless absolute. A non-zero exit, or a path that does not exist, stops the release.
Copy the artifact to `{{release_dir}}/<version>-<its file name>`, record that copy's
absolute path as `<artifact-path>`, and remove the worktree with `git worktree remove
--force <worktree path>`, reporting a failed removal with the path. Remove it the same way
on every exit from this step, a failed build included, as the pre-push checklist's clean
build does. The copy outlives the
run, so the artifact production runs is never lost with the worktree. Every later step
deploys that one path, and this command never runs again in this release — a rebuild is a
different artifact than the one about to be tested.

## Step 4 — Write the release notes

Write `{{release_dir}}/<version>-notes.md` from what this checkout already holds, so
nothing between here and the staging ask needs the network:

```markdown
# v<version>

## Changes
## Migrations
## Known issues
## Rollback
```

- **Changes** — one line per scope key, with each commit subject in the range that names
  it.
- **Migrations** — the summary's `Upgrade notes` section, or `none`.
- **Known issues** — every non-empty defect group under the summary's
  `Open defects by severity`, then its `Known risks`.
- **Rollback** — `{{rollback_command}} <stage>` for each production stage, newest first.

Then read the file back: all four headings present, or the release stops here, per
`gates/release.md` criterion 1.

## Step 5 — Staging, then each production stage

**The staging ask.** Ask `{{roles.release_manager}}` once, printed per
`gates/project-config.md`. The question names:

- the artifact path;
- `{{deploy_command}} staging <artifact-path>`, then `{{smoke_test_command}} staging`, then
  `{{rollback_command}} staging`, then `{{smoke_test_command}} staging` again;
- the rollback of staging that any failure triggers.

Then stop and wait. Run no `{{deploy_command}}` before an answer. A clarifying question is
not an answer, and only the release manager's answer counts; one relayed by the person
running the session is printed as relayed.

On approval, run the four commands in that order from the project root. A failure stops the
release: if staging was deployed and not yet rolled back, run `{{rollback_command}} staging`
first, then report which command failed. A failed `{{deploy_command}} staging` counts as
deployed, since it may have changed staging part-way. A failed rollback is reported as
staging left on the new artifact, and the tag stays, named in the report. Nothing reaches
production. A pass settles `gates/release.md` criterion 1.

**Each production stage**, in order — the first one too, never only the later ones. Every
command from here to the end of Step 6 runs from the project root, never the build worktree:

1. Ask `{{roles.release_manager}}` to approve `<stage>`. The approval covers that stage's
   deploy, its smoke test, its monitoring window, and its rollback on a halt, with no
   further ask. The last stage's question also names the tag push, the published notes,
   and the ticket transition of Step 6, which its approval covers too. Print the role per
   `gates/project-config.md`, then stop and wait as for staging: a clarifying question
   keeps the wait open. An explicit refusal or abort ends the rollout as a halt does, minus
   the halt itself: roll back every production stage
   already deployed, newest first, under their own approvals. That is Argo Rollouts' abort,
   which returns a rollout to its stable version, never one left part-way.
2. `{{deploy_command}} <stage> <artifact-path>`, then `{{smoke_test_command}} <stage>`.
3. Watch the halt criteria for the window with the command below. Run it as one background
   command and wait for it to finish. It keeps no state the session must poll, and nothing
   else runs meanwhile.

Write `{{halt_criteria}}` in as its JSON list and `{{monitoring_window_minutes}}` as its
number: shell variables, `CLAUDE_PROJECT_DIR` among them, are not set in the session's
shell. The list reaches Python on file descriptor 3, so no quoting inside a command can
break it, and both heredoc terminators stay at the start of their lines.

```bash
python3 - {{monitoring_window_minutes}} <<'PY' 3<<'JSON'
import json, os, subprocess, sys, time
window = int(sys.argv[1])
try:
    criteria = json.loads(os.fdopen(3).read())
    assert isinstance(criteria, list) and criteria
    assert all(isinstance(c, str) and c.strip() for c in criteria)
except Exception:
    print("HALT: halt_criteria could not be read as a non-empty list of commands")
    sys.exit(1)
start = time.monotonic()
for minute in range(window + 1):
    round_start = start + 60 * minute
    time.sleep(max(0, round_start - time.monotonic()))
    procs = [subprocess.Popen(["bash", "-c", c], stdin=subprocess.DEVNULL, start_new_session=True)
             for c in criteria]
    for criterion, proc in zip(criteria, procs):
        try:
            code = proc.wait(timeout=max(0, round_start + 55 - time.monotonic()))
        except subprocess.TimeoutExpired:
            code = "no exit within 55 seconds"
        if code != 0:
            for other in procs:
                try:
                    os.killpg(other.pid, 9)
                except ProcessLookupError:
                    pass
            print(f"HALT at minute {minute}: {criterion} ({code})")
            sys.exit(1)
print("window clean")
PY
{{halt_criteria}}
JSON
```

Each round starts on the minute, from minute 0 through the window's end, and runs every
criterion at once. A criterion fires when it exits non-zero or has not exited 55 seconds
into its round, and the watch ends there. A list it cannot read is a halt too: a watch with
nothing to check would pass.

**On a halt — a fired criterion, a failed production deploy, or a failed production smoke
test — roll back first.** Before reading logs, reporting, or anything else, run
`{{rollback_command}} <stage>` for every production stage deployed, the failed one included,
newest first. Each stage's own approval already authorized its rollback. Then report the
criterion or smoke output, each rollback's result, and the stage the release stopped at.
Delete the local tag and stop, unless a rollback failed: then production still runs the
tagged artifact, so the tag stays and is named in the report. A rollback that itself fails
does not stop the older stages' rollbacks, and is reported first, in one line, as the
emergency it is.

## Step 6 — Publish and update the tickets

Once the last stage's window closes clean:

```bash
git push origin v<version>
gh release create v<version> --verify-tag --title v<version> --notes-file {{release_dir}}/<version>-notes.md
gh release view v<version> --json isDraft --jq .isDraft
```

`--verify-tag` refuses to create a tag GitHub does not already have, so the release cannot
point at a different commit. Criterion 4 needs `create` to exit zero in this run and
the view to print `false`. A failure here does not roll back production. Report the
command that failed and the exact one to run, since the release is live and only its notes
are missing. The ticket transitions below still run: the tickets were released either way.

Then, unless `{{released_status}}` is `none`, move each scope ticket there. A ticket already
in that status is left alone. For each other key, use `jira_get_transitions`, then the
transition whose target status, where the result names one, or else whose own name, equals
`{{released_status}}` exactly, by its ID — never a guessed one. Then read the issue back and
confirm its status name is `{{released_status}}`. Report by key any ticket with no such
transition, with the names it does offer, or not in that status afterward, and leave it to
`{{roles.release_manager}}`. With `{{released_status}}` `none`, move nothing; Step 1's
announcement already named it.

Report each criterion of `gates/release.md` and how it stands, the tag, the release URL,
and the tickets moved.
