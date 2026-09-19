---
type: tool_used
tool: Write
min: 0
max: 0
arm: both
---

No file is written. The workspace has no `.claude/project.json`, so there are no
verification tiers, source roots, or registry file to write tickets against, and a draft
written anyway carries `[verify: …]` tags naming tiers the project never declared —
exactly the tickets `plan-work` later cannot fill a `Verified by` cell for.

Write is not granted to this run, so this grader also confirms the case stayed inside its
allowlist rather than silently losing a capability it needed.
