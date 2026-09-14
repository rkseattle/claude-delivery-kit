---
type: tool_used
tool: Bash
input_match: "git (checkout|switch|branch)"
min: 0
max: 0
---

No branch is created or switched during planning. The approval gate at the end of
planning is the one hard stop in the workflow: a branch created before approval means
implementation began without it.
