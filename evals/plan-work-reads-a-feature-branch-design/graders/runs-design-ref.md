---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?project_rules\.py\\?["'']?\s+design-ref\b'
min: 1
arm: with
---

`plan-work` asks `design-ref` which commit to read the design at, rather than reading it
only on `origin/main`, where this design does not exist.
