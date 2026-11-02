---
type: regex
target: files
flags: m
pattern: '^(?!(?:.*/)?docs/design/[^/]+\.md$)(?!(?:.*/)?docs/adr/\d{4}-[^/]+\.md$)(?!(?:.*/)?__pycache__/[^/]+\.pyc$)(?!(?:.*/)?\.git/(?:design-feature-input/|FETCH_HEAD$|worktrees/[^/]+/|design-feature-base-[^/]+/)).+$'
match: not_contains
arm: both
---

The run created no file but a design doc under `docs/design/` and its ADRs under
`docs/adr/`, read from the list of paths created during the run rather than from the
transcript, so a write from inside an interpreter is caught too. Under `.git/`, only what a
compliant run creates is allowed: the skill's input files, what `git fetch` writes, and the
`worktrees/<id>/` entry and `design-feature-base-*/` tree `design_check.py base-tree` adds
and removes, in case the list holds a path created and later deleted.
The scaffold already fetched an origin matching its commit, so any new object, ref, or
stash under `.git/` fails the run. Python's `__pycache__/*.pyc` is allowed too, since running the scaffold's
tests writes it. A file the scaffold made and the run only edited is not in the list, which
`no-other-edit` covers, and a deletion is in neither.
