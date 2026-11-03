---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?design_check\.py\\?"?\s+base-tree\s+remove\b'
min: 2
---

The run removed the base tree at least twice: once in Step 1, clearing any tree a killed run
left, and again before Step 5 presents, so the stop leaves no worktree behind.
This counts the calls, not the end state: `creates-nothing-else` allows the tree's paths,
and `design_check.py --self-test` is what shows `remove` leaves none.
