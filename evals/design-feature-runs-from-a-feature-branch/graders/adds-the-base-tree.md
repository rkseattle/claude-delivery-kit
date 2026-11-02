---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?design_check\.py\\?"?\s+base-tree\s+add\s'
min: 1
---

The run checked the base out as a detached worktree with `design_check.py base-tree add`,
the one place `design-feature` reads the project's code from. Without it the Explore agents
read the working tree, which here holds `wip`'s unmerged code.
