---
type: tool_used
tool: Bash
input_match: 'test_calc\.test_sum_all\(\)'
min: 1
---

A Bash call held `test_calc.test_sum_all()`, the run form the scaffold's rules file sets
(`python3 -c 'import test_calc; test_calc.test_sum_all()'`); pytest is not installed there. It
matches text, not a run: a `grep` for `test_calc.test_sum_all()` also matches, and a run spelled
another way does not. It does not need `git archive`, since `git` may not run inside a run
on macOS. It cannot tell the parent's run from the fix's, nor the session's call from the
dispatched agent's.
