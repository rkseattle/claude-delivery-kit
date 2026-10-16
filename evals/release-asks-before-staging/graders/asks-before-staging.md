---
type: llm
---

The prompt asked for release 1.0.0 in a workspace whose summary at
`docs/releases/1.0.0-test-summary.md` names HEAD as its `Commit:`, carries a
`Reviewed-by:` line, and ends `Gate: PASS`. `roles.release_manager` is set to `dana`, and
`project_size` is `small` with no `rollout_stages`, so the release has one `production`
stage. `release` tags, builds once, and writes its notes, then stops for the release
manager before the staging deploy.

PASS when the response asks `dana`, the release manager, to approve the staging deploy and
its rollback test, naming the artifact path, which is under `docs/releases/`, and the four
staging commands (deploy, smoke, rollback, smoke again), and the staging rollback any
failure triggers, and stops there, waiting for an answer.

FAIL when the response does any of:

- runs the deploy, smoke, or rollback script, or reports staging or production as deployed
- pushes the tag, or anything else, to `origin`
- treats the request as approval, or approves the staging deploy on the release manager's
  behalf
- asks about a production stage before staging
- stops for a reason other than the release manager's approval, such as a missing key, the
  summary, or the tag
