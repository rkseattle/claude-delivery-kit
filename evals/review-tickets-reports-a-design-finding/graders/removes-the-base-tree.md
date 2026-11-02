---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?=(?:[^"\\]|\\.)*?design_check\.py\\?"?\s+base-tree\s+remove\b)(?=(?:[^"\\]|\\.)*?--owner\s+review-tickets\b)'
min: 1
arm: with
---

The skill's base tree is removed once the review returns, so the run leaves none behind.
