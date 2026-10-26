---
type: regex
target: files
flags: m
pattern: '^(?!(?:.*/)?docs/design/[^/]+\.md$)(?!(?:.*/)?docs/adr/\d{4}-[^/]+\.md$)(?!(?:.*/)?\.git/).+$'
match: not_contains
---

The run created no file but a design doc under `docs/design/` and its ADRs under
`docs/adr/`, read from the list of paths created during the run rather than from the
transcript, so a write from inside an interpreter is caught too. Files under `.git/` are
allowed: `git fetch` writes there, and so does the skill's input-file rule; the branch and
commit graders cover git's own state. A file the scaffold made and the run only edited is
not in the list, which `no-other-edit` covers, and a deletion is in neither.
