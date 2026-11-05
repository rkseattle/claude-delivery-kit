---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?project_rules\.py\\?["'']?\s+lifecycle\s+--ref\s+\\?["'']?[0-9a-f]{40}\b'
min: 1
arm: with
---

`lifecycle` runs at the full commit hash `design-ref` printed for the feature branch, so
the state comes from the branch's design.
