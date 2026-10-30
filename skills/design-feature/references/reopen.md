# Reopen mode

A design already on `origin/{{parent_branch_default}}` is revised as a merged KEP is: on a
branch of its own whose first commit moves `status` back to `proposed`, then reviewed and
decided again, and merged by pull request. Nothing in this mode edits
`{{parent_branch_default}}`.

## When it applies

Every condition holds:

1. `$ARGUMENTS` names an existing design: its path under `{{design_dir}}`, or the Epic its
   `Epic:` line names.
2. That design is on `origin/{{parent_branch_default}}`. Its status there, as
   `project_rules.py design-read --status` prints it, is `accepted`, or `proposed` from a
   hand edit made on the parent before this mode existed.
3. The person running the session confirmed the reopen, or `project_rules.py lifecycle`
   printed `tickets-stalled-needs-design-rework`: a `write-tickets` draft holds a
   `<!-- design-rework: ... -->` line for the design as it stands on the parent.

A `rejected` design is never reopened. It is the record of a stop; a new request starts a
new design.

## Steps

1. **Continue an open revision.** A local `design/<slug>-rev<N>` is open when
   `project_rules.py design-read --ref design/<slug>-rev<N> --status`, given the design's
   path, prints `proposed`: its reopen commit is there and no decision is. Switch to the
   highest open `N` and skip to step 5. A revision whose tip is decided but whose design
   differs from the parent's (`git diff --quiet origin/{{parent_branch_default}}
   design/<slug>-rev<N> -- <path>` exits 1) is awaiting its pull request: stop and say to
   merge it first.
2. **Cut the branch.** `N` is the lowest number from 2 up — `design/<slug>` is the first
   revision — for which neither
   `design/<slug>-rev<N>` nor `origin/design/<slug>-rev<N>` exists. Run
   `git switch -c design/<slug>-rev<N> <base>`, with `<base>` the commit Step 1 recorded.
3. **Reopen on the branch.** Edit the design doc only:
   - Set `status: proposed`.
   - Set `## Decision` to `Pending — <tech lead>.`
   - Add `## Revision history` before `## Decision` if it is missing.
   - Append `- <date from date +%F>: <reason>`. The reason quotes each BLOCKER in the
     draft's last `<!-- review round N -->` block for the tickets its `design-rework` line
     names. Without that line, it quotes the reason the person gave.

   Leave every ADR as it is. An accepted ADR is never edited here.
4. **Commit the reopen.** Run `project_rules.py design-transition` as Step 6 does. It must
   print `ok accepted -> proposed`, or `ok proposed -> proposed` for a hand-edited parent.
   Write the message — `Reopen the <title> design`, a blank line, and the reason — to a
   file with the Write tool, per **Untrusted text** in `gates/project-config.md`, since
   the reason is free text. Commit the design doc alone with `git commit -F <file>`.
5. **Revise.** Run Steps 2–5 on the reopened doc as on any draft. A change that would
   reverse an accepted ADR's choice is superseding, which `gates/design-exit.md` puts out
   of scope: stop and bring it to Rob. A new `- Costly to reverse:` line gets a new ADR,
   numbered by the gate's rule.
6. **Record and commit.** Step 6 runs as written, with these differences:
   - Its `branch` file names `design/<slug>-rev<N>`.
   - It commits on that branch rather than cutting one.
   - It skips the already-committed stop, which a reopened design always meets, and stops
     on `origin/design/<slug>-rev<N>` existing rather than `origin/design/<slug>`.
   - It sets `status` on the design and on ADRs this revision added only.
   - It runs `design-transition` with `--ref HEAD`, the reopen commit, so the move it
     checks is `proposed → accepted` or `rejected` on the revision branch.

The branch reaches `{{parent_branch_default}}` by an ordinary pull request. Once it merges,
`write-tickets` reads the revised design, and the draft's `design-rework` line no longer
matches it.
