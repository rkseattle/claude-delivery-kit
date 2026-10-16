# Planning exit — the rule book's Phase 1 gate

Rule book Phase 1: "No implementation work starts until scope, success measures, and top
risks are written and approved by the sponsor." Its exit criteria are the four below, quoted
from the rule book. Read this file before asking `{{roles.sponsor}}` to approve a brief, and
check every criterion against `{{brief_file}}` and the repository, not against memory of
what was written. With `{{brief_file}}` `none` there is no brief, and the gate cannot pass.

## Exit criteria

- [ ] Brief approved by sponsor
- [ ] Non-goals stated
- [ ] Risk list with owners exists
- [ ] Repository and CI pipeline run a passing empty build

## What settles each one

1. **Brief approved by sponsor** — the brief's `## Decision` section reads `Approved`, with
   the sponsor and the date. It reads `Pending` until the sponsor answers; a brief with no
   `## Decision` section fails. `Rejected` closes the gate for good: revision is asked for
   as rework, before a decision, never after one. Waiving a Phase 1 rule
   instead is the sponsor's alone, recorded in `{{exceptions_log}}` in the format
   `${CLAUDE_PLUGIN_ROOT}/gates/exceptions.md` defines.
2. **Non-goals stated** — `## Non-goals` holds at least one item that names something. An
   empty section, or an item reading "none", "TBD", or "N/A", fails: a brief with no stated
   non-goals has not bounded its scope. A `(proposed)` item counts; the sponsor's approval
   confirms it.
3. **Risk list with owners exists** — `## Risks` is a table of five rows, each with a
   `Likelihood` of low, medium, or high, an `Impact`, a `Mitigation`, and an `Owner` naming
   a person or role.
4. **Repository and CI pipeline run a passing empty build** — with
   `{{parent_branch_default}}` checked out, its HEAD equal to
   `origin/{{parent_branch_default}}`, and `git status --porcelain --untracked-files=all`
   listing nothing but `{{brief_file}}`:
   - `{{build_command}}` passes;
   - `gh run list --branch {{parent_branch_default}} --limit 1 --json conclusion` reports
     `success`;
   - every run on that HEAD commit,
     `gh run list --commit "$(git rev-parse HEAD)" --json workflowName,conclusion`,
     concluded `success` or `skipped` — GitHub's rule for a commit's combined check status,
     under which a skipped run passes.

   No run on the commit fails. A run still in progress has no conclusion yet: wait for it
   with `gh run watch <id> --exit-status`, then check again. A `cancelled` run fails until
   it is re-run. A `gh` error — not installed, not signed in, no GitHub remote — is named as
   that, not as a red pipeline.

Criteria 2 and 3 are checked before the sponsor is asked, and a failure is fixed in the
brief. A failing criterion 4 stops the gate, named as the reason the brief cannot be
presented. Setting up or repairing the build and pipeline is rule book Phase 1 step 6, done
outside this gate, which only checks it; the brief is presented again once it passes.
