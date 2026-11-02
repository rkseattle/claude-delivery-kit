---
type: regex
target: files
flags: m
pattern: '^(?!(?:.*/)?__pycache__/[^/]+\.pyc$)(?!(?:.*/)?\.git/(?:review-tickets(?:-input)?/|FETCH_HEAD$|worktrees/[^/]+/|review-tickets-base-[^/]+/)).+$'
match: not_contains
arm: both
---

The run created no file outside what a compliant review creates, read from the list of
paths created during the run rather than from the transcript, so a write from an
interpreter or a subagent is caught too: its input files and draft under
`.git/review-tickets-input/` and `.git/review-tickets/`, what `git fetch` writes, and the
`worktrees/<id>/` entry and `review-tickets-base-*/` tree `design_check.py base-tree` adds
and removes. Python's `__pycache__/*.pyc` is allowed, since a reviewer may run the tests.
The pattern is `design-feature-runs-from-a-feature-branch`'s `creates-nothing-else`, its
allowances naming this skill's paths.
