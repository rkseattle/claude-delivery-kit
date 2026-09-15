# Read-only agent — never change the repository state

Every adversary agent in this plugin is a reader. You share a working tree with a live
session, and moving HEAD leaves that session on the wrong branch — that has happened, and
the session's next commit landed somewhere nobody intended.

Every command must leave the working tree, the index, the checked-out branch, and the
stash exactly as you found them.

**Never run** `git checkout`, `git switch`, `git restore`, `git stash`, `git reset`,
`git clean`, `git worktree`, or any command that writes a tracked file.

Read any ref in place instead:

```bash
git show <ref>:<path>          # a file at that ref
git diff <base>...<branch>     # the change set
git log <base>..<branch>       # the commits
git grep <pattern> <ref> -- <path>
```

Reading the checked-out tree with `Read` and `Grep` is fine; only moving HEAD is
forbidden. If a question genuinely cannot be answered without a checkout, say so and
leave it unanswered rather than switching.
