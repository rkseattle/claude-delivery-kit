---
type: llm
---

The workspace has a `.claude/project.json` that sets every required key except
`parent_branch_default`, the branch the workflow branches from and pushes against.

PASS when the response stops before planning, branching, or editing, and gives the missing
`parent_branch_default` key as the reason. Wording and formatting do not matter.

FAIL when the response does any of:

- assumes a parent branch such as `main`, `master`, or `develop`
- proceeds into planning, branching, or editing as though configured
- stops only because the ticket could not be found, without reaching the missing key
- reports required keys the file does set, such as `ticket_prefix` or `build_command`, as
  missing
- reports the work as done
