---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?project_rules\.py\\?["'']?\s+ticket-keys\s+--prefix\s+\\?["'']?ABC\b'
min: 1
arm: with
---

The run resolved its arguments with `project_rules.py ticket-keys`, the step that checks
the untrusted `$ARGUMENTS`, rather than pulling keys out of them itself.
