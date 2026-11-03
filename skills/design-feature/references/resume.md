# Resume or abort an interrupted Step 6

Step 6 keeps everything its commit needs in the directory
`git rev-parse --path-format=absolute --git-path design-feature` names, as git's sequencer
keeps a commit's `message` where it can finish without the session that began it. When
that directory exists, Step 6 started and did not finish, the way `.git/rebase-merge`
tells git a rebase is in progress.

- **Design:** the one its `slug` file names.
- **Branch:** the one its `branch` file names, or `design/<slug>` when there is no such
  file.

First run `design_check.py base-tree remove --tree "<the path its tree file names>"
--if-stale --config "<absolute project root>/.claude/project.json"`, or with no `tree` file,
a run killed before it recorded one, the same with `--branch "<branch>"` in place of
`--tree`, so the branch is checked out nowhere. Its `INVALID:` means the tree is live and another session's
Step 6 may be in progress: stop and say so, as git refuses a rebase while
`.git/rebase-merge` exists; the person who knows that session is gone runs the same command
without `--if-stale`, then runs again. Then run the bare `remove` Step 1 runs, clearing a stale
tree. Then take the first row that applies:

| Condition | Then |
| --------- | ---- |
| `git show <branch>:./{{design_dir}}/<slug>.md` holds the first line of `decision` | The commit landed and only cleanup was lost. Remove the directory, delete the checkout's copies as Step 6 does once its commit succeeds, report that commit, and offer no abort. |
| The person asks to abort | Abort, below. |
| The branch is a missing `design/<slug>-rev<N>` | Its reopen commit is lost. Stop, and say to abort and reopen again. |
| Otherwise | Continue, below. |

**Continue.** Keep the recorded decision.

1. In reopen mode, or with the branch checked out as a run of an earlier release left it,
   switch to the branch and commit there in step 3. Otherwise delete `design/<slug>` when
   it holds no commit `base` lacks, and cut it again in a new base tree, as Step 6 does.
2. Make every edit Step 6 makes from `decision` and `status`.
3. Commit as Step 6 does, from `message`.

**Abort.** Leave index and tree as they were before Step 6, as `git rebase --abort` does.

1. With the branch checked out — reopen mode, or a run of an earlier release — unstage the
   design doc and its ADRs with `git restore --staged`.
2. Restore each from `presented/`.
3. In reopen mode, stay on the revision branch, where Step 6 began, as `git rebase --abort`
   returns to where the rebase began. With `design/<slug>` checked out, as a run of an
   earlier release left it, switch to `{{parent_branch_default}}`, where that run began.
   Otherwise the checkout never left its own branch.
4. Delete the branch if it has no commits of its own.
5. Remove the directory.

No other stop applies while the directory exists, and `$ARGUMENTS` is not needed.
