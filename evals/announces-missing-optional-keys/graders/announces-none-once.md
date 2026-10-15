---
type: llm
---

The workspace's `.claude/project.json` sets every required key and leaves out every
optional one, including `registry_file`, `plan_rules_file` and `disciplines`, which
`plan-work` reads.

PASS when the response names, in a single line or sentence, each absent optional key it
uses and the value it took (`none` for the first two, `[]` for `disciplines`), naming them
together. It may then stop for another reason, such as
the ticket being unreachable. Wording and formatting do not matter.

FAIL when the response does any of:

- invents a path or value for `registry_file`, `plan_rules_file` or `disciplines`
- announces each missing key on its own separate line
- stops because a required key is missing (none is)
- never mentions the missing optional keys
