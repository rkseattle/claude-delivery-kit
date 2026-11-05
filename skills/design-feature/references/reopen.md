# Reopen mode

A design already at `<design ref>`, Step 1's — `origin/{{parent_branch_default}}`, or the
commit of the checked-out branch holding its own copy — is revised as a merged KEP is: on a
branch of its own whose first commit moves `status` back to `proposed`, then reviewed and
decided again, and merged by pull request into the branch it came from. Nothing in this
mode edits `{{parent_branch_default}}` or that branch.

## When it applies

Every condition holds:

1. `$ARGUMENTS` names an existing design: its path under `{{design_dir}}`, or the Epic its
   `Epic:` line names.
2. That design is at `<design ref>`. Its status there, as
   `project_rules.py design-read --status` prints it, is `accepted`, or `proposed` from a
   hand edit made on the parent before this mode existed.
3. The person running the session confirmed the reopen, or `project_rules.py lifecycle`
   printed `tickets-stalled-needs-design-rework`: a `write-tickets` draft holds a
   `<!-- design-rework: ... -->` line for the design as it stands at `<design ref>`.

A `rejected` design is never reopened. It is the record of a stop; a new request starts a
new design.

## Steps

1. **Continue an open revision.** A local `design/<slug>-rev<N>` is open when
   `project_rules.py design-read --ref design/<slug>-rev<N> --status`, given the design's
   path, prints `proposed`: its reopen commit is there and no decision is. Switch to the
   highest open `N`, stopping as step 2 does when git refuses the switch, record the base
   as Step 1 does for a revision branch, add the base tree at
   it as Step 1 does, and skip to step 5. A revision whose tip
   is decided but whose design differs from the parent's
   (`git diff --quiet <design ref> design/<slug>-rev<N> -- <path>`
   exits 1) is awaiting its pull request: stop and say to merge it first.
2. **Cut the branch.** `N` is the lowest number from 2 up — `design/<slug>` is the first
   revision — for which neither `design/<slug>-rev<N>` nor `origin/design/<slug>-rev<N>`
   exists. Run `git switch -c design/<slug>-rev<N> <base>`, with `<base>` the commit Step 1
   recorded. When `<design ref>` is a commit, first stop unless `git symbolic-ref -q HEAD`
   exits 0, since a detached HEAD names no branch to merge back into; after the switch, set
   `<key>`, `branch.design/<slug>-rev<N>.gh-merge-base`, to the branch switched from, git
   naming it so it never passes through this text —
   `git config "<key>" "$(git rev-parse --abbrev-ref @{-1})"` — or, when Step 1 found this
   design's own `design/<slug>` or a revision of it checked out, to that branch's target,
   carried forward:
   `target=$(git config --get "branch.$(git rev-parse --abbrev-ref @{-1}).gh-merge-base") && git config "<key>" "$target"`,
   stopping when it fails: `gh pr create` opens the revision's pull request against it, as
   Git Town's `set-parent` records a branch's parent apart from its push upstream. When git
   refuses the switch over local changes, stop and name the files it lists; the person
   commits or stashes them, never this run.
3. **Reopen on the branch.** Edit the design doc only:
   - Set `status: proposed`.
   - Set `## Decision` to `Pending — <tech lead>.`
   - Add `## Revision history` before `## Decision` if it is missing.
   - Append `- <date from date +%F>: <reason>`. The reason quotes the findings
     `write-tickets` wrote just above the draft's matching `design-rework` line. Without
     that line, it quotes the reason the person gave.

   Leave every ADR as it is. An accepted ADR is never edited here.
4. **Commit the reopen.** Run `project_rules.py design-transition` as Step 6 does, with
   `--ref "<design ref>"` and no `--worktree`. It must print
   `ok accepted -> proposed`, or `ok proposed -> proposed` for a hand-edited parent. Write
   the message — `Reopen the <title> design`, a blank line, and the reason — to a file with
   the Write tool, per **Untrusted text** in `gates/project-config.md`, since the reason is
   free text. Commit the design doc alone with `git commit -F <file> -- <design path>`, so
   a change staged on the branch the run started from stays out of it.
5. **Revise.** Run Steps 2–5 on the reopened doc as on any draft. A change that would
   reverse an accepted ADR's choice is superseding, which `gates/design-exit.md` puts out
   of scope: stop and bring it to Rob. A new `- Costly to reverse:` line gets a new ADR,
   numbered by the gate's rule.
6. **Record and commit.** Step 6 runs as written, with these differences:
   - Its `branch` file names `design/<slug>-rev<N>`.
   - It commits on that branch, checked out, rather than cutting one in a base tree.
   - It skips the already-committed stop, which a reopened design always meets, and stops
     on `origin/design/<slug>-rev<N>` existing rather than `origin/design/<slug>`.
   - It sets `status` on the design and on ADRs this revision added only.
   - It runs `design-transition` with `--ref HEAD`, the reopen commit, and no `--worktree`,
     so the move it checks is `proposed → accepted` or `rejected` on the revision branch.

The branch reaches the branch its `gh-merge-base` names, or `{{parent_branch_default}}`, by an
ordinary pull request. Once it merges,
`write-tickets` reads the revised design, and the draft's `design-rework` line no longer
matches it.
