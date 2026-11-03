---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?=(?:[^"\\]|\\.)*?design_check\.py\\?["'']?\s+base-tree\s+add\b)(?=(?:[^"\\]|\\.)*?--owner\s+review-tickets\b)'
min: 1
arm: with
---

The design is read from the commit `design-read` judged, checked out as the skill's own
base tree, owned by `review-tickets`, rather than from the checkout or `design-feature`'s
tree.
