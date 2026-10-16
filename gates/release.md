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

Before the release is tagged, each of these stops it and names the key:

- `{{release_artifact_command}}`, `{{deploy_command}}`, `{{smoke_test_command}}`,
  `{{rollback_command}}`, or `{{release_dir}}` of `none`;
- `{{halt_criteria}}` of `none`, an empty list, or an entry that is empty or only spaces;
- `{{monitoring_window_minutes}}` that is not a positive whole number;
- `{{rollout_stages}}` as an empty list, or with an entry named `staging`, which would
  count staging as production.

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
   there. Then `{{deploy_command}} staging <artifact-path>` succeeded,
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
   `{{monitoring_window_minutes}}` minutes and none fired. A command fires when it exits
   non-zero, or when it has not exited 55 seconds after it started: a check that cannot
   finish within its minute cannot be run once a minute. The run's first action is then
   `{{rollback_command}} <stage>` for each deployed production stage, newest first, and the
   gate has failed for this release whatever the rollback's outcome. A rollback that fails
   does not stop the older stages' rollbacks. Each one's result is reported, and the first
   failure is reported as the emergency it is.
4. **Release notes published** — after `git push origin v<version>`,
   `gh release create v<version> --verify-tag --notes-file {{release_dir}}/<version>-notes.md`
   exits zero in this run, and `gh release view v<version> --json isDraft --jq .isDraft`
   then prints `false`. A release that already existed is not one this run published. A
   failure here leaves production on the new version, rolled out and monitored clean: it is
   reported with the exact command still to run, and nothing is rolled back.

Criterion 1 is checked before any production stage, and a failure stops the release there:
staging is rolled back where it can be, nothing reaches production, and nothing is
published. Criteria 2 and 3 are checked per stage, so a failure stops the rollout at the
stage that failed. Criterion 4 runs only once the last stage's window has closed clean.
