---
description: A named test that is red on the parent only because it imports a new symbol does not verify the fix
max_turns: 25
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
tags:
  - adversarial-review
  - regression
---

You are acting as the `ci-failure-adversary` agent. Its definition is at
`agents/ci-failure-adversary.md` in this repo — read it and follow it exactly.

The workspace is a git repository. The fix to verify is `HEAD`. GitHub is unavailable in
this environment, so the failure evidence from CI is reproduced below; treat it as if you
had retrieved it yourself. That run was on `HEAD~1`, the fix's parent. The project has no
rules file; its tests are plain Python functions, and pytest is not installed, so run one
with `python3 -c 'import test_calc; test_calc.test_sum_all()'`.

```
FAILED test_report.py::test_invoice_total - assert 5 == 9
 +  where 5 = invoice_total([{'amount': 2}, {'amount': 3}, {'amount': 4}])
1 failed in 0.02s
```

Return your verdict in the format the agent definition specifies.
