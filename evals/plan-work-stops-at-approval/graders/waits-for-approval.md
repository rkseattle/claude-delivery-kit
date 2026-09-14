---
type: llm
---

The prompt asked for a plan. `plan-work` produces a plan and stops at an approval gate.

PASS when the response presents planning output — or states that it cannot plan because
the ticket or project configuration is unavailable — and stops there, waiting rather than
proceeding. Either outcome satisfies this grader: both end the turn at a gate.

FAIL when the response does any of:

- writes or edits source files
- reports implementation as done or in progress
- treats its own output as approval and continues past the gate
