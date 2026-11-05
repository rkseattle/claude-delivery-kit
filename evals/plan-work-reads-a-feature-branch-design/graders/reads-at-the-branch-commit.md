---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?project_rules\.py\\?["'']?\s+design-read\s+--ref\s+\\?["'']?(?:[0-9a-f]{40}\b|\$)'
min: 1
arm: with
---

`design-read` runs at the full commit hash `design-ref` printed, written out or held in a shell
variable, for the feature branch, so
the design is read where it exists.
