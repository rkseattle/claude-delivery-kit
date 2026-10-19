# Release — the rule book's Phase 6 gate

Rule book Phase 6: "Deployments must be automated, repeatable, and reversible. Every
release must have a tested rollback path before it starts." Its exit criteria are the four
below, quoted from the rule book. `release` reads this file before it tags and
checks every criterion against what that run executed and read back, never against memory
of an earlier release.

## Exit criteria

- [ ] Rollback tested in staging
- [ ] Smoke tests pass in production
- [ ] No halt criterion triggered during the monitoring window
- [ ] Release notes published

## What settles each one

Before the release is tagged, each of these stops it and names the key or the check:

- HEAD not reachable from a freshly fetched `origin/{{parent_branch_default}}`, since a
  release is cut from the reviewed mainline;
- a summary whose last two lines, version, and SHA-256 do not match the note
  `release-readiness` wrote on HEAD under `refs/notes/release-readiness`, or no such note;
- `{{release_artifact_command}}`, `{{deploy_command}}`, `{{smoke_test_command}}`,
  `{{rollback_command}}`, or `{{release_dir}}` of `none`;
- `{{halt_criteria}}` of `none`, anything but a JSON list of strings, an empty list, or an
  entry that is empty, only spaces, or a `<placeholder>`;
- `{{monitoring_window_minutes}}` that is not a positive whole number;
- `{{rollout_stages}}` that is neither `none` nor a JSON list of strings, an empty list, or
  a list with an entry that is blank, repeated, named `staging` (which would count staging
  as production, in any case), starting with `-` or `.`, or not made only of letters,
  digits, `.`, `_`, and `-`, since each name
  is passed to the commands as a bare argument;
- `${CLAUDE_PLUGIN_ROOT}/skills/release-readiness/scripts/readiness_check.py` `disciplines
  --gate release` printing anything but `ok`: an unknown discipline, or a key a named one
  needs below that is absent, `none`, a `<placeholder>`, or malformed.

Each of those would let a criterion pass with nothing checked. The production stages are
`{{rollout_stages}}` in order. With it `none`, a `{{project_size}}` of `small` gets the
single stage `production`, since the rule book's "Tailoring and exceptions" makes staged
rollout optional at that size. A `medium` or `large` project stops before tagging, until
`{{roles.release_manager}}` explicitly approves one `production` stage for this release.

The tag `v<version>` is new: absent locally and on origin when the run starts. It stays
local until criterion 4 pushes it, and every stop before that push deletes it, so the same
version can run again.

1. **Rollback tested in staging** — in this run, with the release's one artifact, built
   once by `{{release_artifact_command}}` exiting zero, with its last printed line naming a
   file that exists. Before the staging deploy, `{{release_dir}}/<version>-notes.md` has
   the headings `## Changes`, `## Migrations`, `## Known issues`, and `## Rollback`, since
   the rule book writes the notes before staging; a file missing one stops the release
   there. Then `{{deploy_command}} staging "<artifact-path>"` succeeded,
   `{{smoke_test_command}} staging` passed, `{{rollback_command}} staging` succeeded, and
   `{{smoke_test_command}} staging` passed again after it. The second smoke run is what
   makes the rollback tested: a rollback that exits zero and leaves staging broken is not a
   rollback path. A failed `{{rollback_command}} staging` is reported as staging left on the
   new artifact.
2. **Smoke tests pass in production** — `{{smoke_test_command}} <stage>` exited zero after
   every production stage's deploy, in stage order. A failure is a halt, handled as
   criterion 3's is.
3. **No halt criterion triggered during the monitoring window** — after each production
   stage, every `{{halt_criteria}}` command ran once a minute for
   `{{monitoring_window_minutes}}` minutes and none fired, settled only by a watch that
   exits 0 with a last line of `window clean`. A watch that ends any other way, crashed or
   killed included, is a halt. A command fires when it exits
   non-zero, or when it has not exited 55 seconds after it started: a check that cannot
   finish within its minute cannot be run once a minute. The run's first action is then
   `{{rollback_command}} <stage>` for each deployed production stage, newest first, and the
   gate has failed for this release whatever the rollback's outcome. A rollback that fails
   does not stop the older stages' rollbacks. Each one's result is reported, and the first
   failure is reported as the emergency it is.
4. **Release notes published** — after the `--atomic` push of `v<version>` and the readiness
   notes ref, `gh release create v<version> --verify-tag --title v<version> --notes-file
   {{release_dir}}/<version>-notes.md` exits zero in this run, and `gh release view
   v<version> --json isDraft --jq .isDraft` then prints `false`. A release that already
   existed is not one this run published. A failure here leaves production on the new
   version, rolled out and monitored clean: it is reported with the exact command still to
   run, and nothing is rolled back.

Criterion 1 is checked before any production stage, and a failure stops the release there:
staging is rolled back where it can be, nothing reaches production, and nothing is
published. Criteria 2 and 3 are checked per stage, so a failure stops the rollout at the
stage that failed. Criterion 4 runs only once the last stage's window has closed clean.

## Discipline addenda

Rule book Appendix B changes Deployment for some disciplines. Each section below applies
only when `{{disciplines}}` names it; a section whose discipline is absent is skipped without
output — no stop, no question, and no line in the report. Every stop here comes before the
tag, except where a section says otherwise.

### security

Appendix B1: security sign-off for a release that changes authentication, authorization, or
data handling. `readiness_check.py sensitive-paths` lists every path the release scope's
range changed, deletions and both sides of a move included, that matches a pattern in
`{{security_sensitive_paths}}`, a space-separated list read as CODEOWNERS reads its
patterns: `*.pem` matches at any depth, `/keys/` only at the root, `src/auth/` everything
below that directory. With a first release the range is all of
history. Any path listed requires `{{roles.security}}`'s explicit sign-off before the tag,
recorded as the last line of `{{release_dir}}/<version>-security-signoff.md`, after the
paths: `Signed-off-by: security <name> <YYYY-MM-DD>`, with `, relayed by <git user.name>`
for a relayed answer. A refusal, or a check that fails, stops the release. None listed: no
sign-off is asked for.

### mobile

Appendix B3: phased store release, remote feature flags, and a server API compatible with
every supported app version.

- `{{api_compat_command}} {{min_supported_app_version}}` exits zero before the tag, and
  again before the first production stage's deploy, after that stage's approval.
- `{{rollout_stages}}` lists at least two stages, whatever `{{project_size}}` is, and
  `none` stops: the production stages are the store's phased release, a partial phase
  before the full one, and `{{rollback_command}} <stage>` halts that phase, since a shipped
  binary cannot be recalled. `halt_watch.py --check` decides it.
- The notes hold `## Remote flags`, with a `- <KEY>: <flag>` line for every scope key: the
  flag a `Remote-flag:` trailer on its commits names, or, for a key with none,
  `{{roles.release_manager}}`'s answer — the flag, or `none — <reason>`. Before staging,
  `readiness_check.py notes-headings --flag-keys` passing settles that every key has a line
  that is no placeholder, with criterion 1's headings; the release manager's answer, not the
  check, settles that a reason was given.

### embedded

Appendix B4: firmware updates are atomic with a fallback image. The staging question asks
`{{roles.release_manager}}` to confirm that the artifact installs atomically with a fallback
image — A/B partitions or equivalent — so a failed update leaves the device on the previous
image. An approval that does not confirm it is not an answer, and the wait stays open.

### sre

Appendix B5: the remaining error budget is a release gate. `{{error_budget_command}}` prints
the remaining budget as one number; `readiness_check.py error-budget` reads it. A non-zero
exit from the command, or an `INVALID:` line from the check, stops the release, since an
unread budget is not a remaining one.
At `0` or below the budget is spent, and the release stops unless every scope ticket carries
the `reliability` label, read from Jira for this run; a ticket that cannot be read counts as
unlabeled. The budget is read again before every production stage's deploy, after that
stage's approval, so a budget spent during the waits stops the rollout there as an abort
does. Only reliability work ships until the budget recovers, as the Google SRE Workbook's
error budget policy has it.
