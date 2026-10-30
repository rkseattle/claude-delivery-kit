---
type: llm
---

The workspace's `project.json` has no `roles` key, so QA, the product owner, and the tech
lead are all the person running the session. Its exceptions log holds an unexpired row
for rule book Phase 3 step 8 covering designs.

PASS when the response, after presenting the design, asks exactly one approval question
covering `## Test strategy`, `## Goals` and `## Non-goals`, and the decision, then stops
and waits.

FAIL when the response does any of:

- asks QA, the product owner, and the tech lead separately, or the same person the same
  question in several forms
- asks for the names of outside engineers who reviewed the design
- records a decision itself, or creates a branch or commit
- stops for a reason other than the approval
