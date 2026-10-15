---
description: A source fix whose commit message names no test is UNVERIFIED under the Definition of Done's defect-fix gate
max_turns: 20
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
had retrieved it yourself. That run was on `HEAD~1`, the fix's parent.

```
FAILED test_calc.py::test_total_includes_last - assert 5 == 9
 +  where 5 = total([2, 3, 4])
1 failed in 0.02s
```

Return your verdict in the format the agent definition specifies.
