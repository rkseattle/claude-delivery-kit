# Resume or abort an interrupted Step 6

Step 6 keeps everything its commit needs in the directory
`git rev-parse --path-format=absolute --git-path design-feature` names, as git's sequencer
keeps a commit's `message` where it can finish without the session that began it. When
that directory exists, Step 6 started and did not finish, the way `.git/rebase-merge`
tells git a rebase is in progress.

- **Design:** the one its `slug` file names.
- **Branch:** the one its `branch` file names, or `design/<slug>` when there is no such
  file.

Take the first row that applies:

| Condition | Then |
| --------- | ---- |
| `git show <branch>:{{design_dir}}/<slug>.md` holds the first line of `decision` | The commit landed and only cleanup was lost. Remove the directory, report that commit, and offer no abort. |
| The person asks to abort | Abort, below. |
| The branch is a missing `design/<slug>-rev<N>` | Its reopen commit is lost. Stop, and say to abort and reopen again. |
| Otherwise | Continue, below. |

**Continue.** Keep the recorded decision.

1. Switch to the branch. Cut it from the commit in `base` when it is a missing
   `design/<slug>`.
2. Make every edit Step 6 makes from `decision` and `status`.
3. Commit as Step 6 does, from `message`.

**Abort.** Leave index and tree as they were before Step 6, as `git rebase --abort` does.

1. Unstage the design doc and its ADRs with `git restore --staged`.
2. Restore each from `presented/`.
3. Switch to `{{parent_branch_default}}`.
4. Delete the branch if it has no commits of its own.
5. Remove the directory.

No other stop applies while the directory exists, and `$ARGUMENTS` is not needed.
