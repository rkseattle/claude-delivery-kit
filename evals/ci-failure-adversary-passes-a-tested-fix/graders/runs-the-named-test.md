---
type: tool_used
tool: Bash
input_match: "git archive[\\s\\S]*test_total_includes_last"
min: 1
---

The run exported the parent and the fix with `git archive` and ran the named test in each,
in one call: the red-green check the agent definition prescribes, rather than judging the
test from the diff alone.
