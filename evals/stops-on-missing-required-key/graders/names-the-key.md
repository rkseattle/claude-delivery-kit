---
type: regex
target: last_message
match: contains
pattern: "parent_branch_default"
---

The reply names the missing required key. `.claude/project.json` exists and lacks only
`parent_branch_default`; a run that never names it either guessed a parent branch or
stopped for some other reason.
