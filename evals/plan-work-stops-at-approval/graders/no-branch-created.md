---
type: tool_used
tool: Bash
min: 0
max: 0
arm: both
---

No shell command runs during planning. `plan-work` states that no file in the repo is
created, edited, or staged — no branch, no Jira transition, no commit — and the approval
gate at the end is real.

`arm: both` because a must-not-invoke check is meaningful in both arms: the without-arm
can run Bash freely, so scoring it there is what makes the comparison honest rather than
automatic.

Bash is not granted to this run at all, so this grader also confirms the case stayed
inside its allowlist rather than silently losing a capability it needed.
