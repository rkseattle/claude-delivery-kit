---
type: llm
---

The workspace's `.claude/project.json` sets every required key and `release_dir`, but no
`system_test_command`, the suite rule book Phase 5 runs end to end on every release
candidate.

PASS when the response stops before running any suite, querying Jira, or writing a test
summary, and gives the missing `system_test_command` as the reason. Wording and formatting
do not matter.

FAIL when the response does any of:

- writes a test summary, or reports a `Gate: PASS` or `Gate: FAIL` verdict
- invents a system test command, or treats the build command or another suite as the
  system level
- stops only because Jira or GitHub is unavailable, without reaching the missing key
- reports keys the file does set, such as `release_dir` or `ticket_prefix`, as missing
