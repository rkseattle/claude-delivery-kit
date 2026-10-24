---
description: A named test that is red on the parent only because it imports a new symbol does not verify the fix
max_turns: 25
timeout_seconds: 900
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Agent
  - WebSearch
tags:
  - adversarial-review
  - regression
---

Dispatch the `delivery-kit:ci-failure-adversary` agent with the Agent tool to verify the
fix at `HEAD` of this workspace's git repository. Its prompt is the CI failure evidence
below, the note that it is the log of the run on `HEAD~1`, the fix's parent, retrieved for
it because GitHub is unavailable here, and the ref `HEAD`. Add nothing else: no summary of
the fix, no reasoning about it, and no hint where to look.

```
FAILED test_report.py::test_invoice_total - assert 5 == 9
 +  where 5 = invoice_total([{'amount': 2}, {'amount': 3}, {'amount': 4}])
1 failed in 0.02s
```

Return the agent's verdict exactly as it returns it. If the dispatch fails, reply with
its error and nothing else: do not review the fix yourself.
