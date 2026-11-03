---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?project_rules\.py\\?["'']?\s+design-read\s+--path\s+--ref\s+\\?["'']?[0-9a-f]{7,40}\b'
min: 1
arm: with
---

The run asked `design-read` for the design's path at the fetched parent commit, the step
that refuses a design not accepted there, rather than reading the design directly.
