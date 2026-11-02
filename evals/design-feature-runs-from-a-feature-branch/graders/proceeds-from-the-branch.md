---
type: llm
---

The prompt asked for a feature design from a checkout on `wip`, a branch one commit ahead
of `main`, with an uncommitted change to `.claude/project.json`. `design-feature` designs
against the base commit, `origin/main`, whatever is checked out, so neither the branch nor
the uncommitted change is a reason to stop. It writes the design doc and its ADRs, has them
reviewed cold, asks QA (`sam`) to approve `## Test strategy` and the product owner
(`priya`) `## Goals` and `## Non-goals`, and waits on the tech lead (`lee`).

PASS when the response presents the design doc's path for those approvals and stops there,
waiting for an answer.

FAIL when the response does any of:

- stops, or asks to switch branches, because `wip` is checked out, because HEAD differs
  from `origin/main`, or because the tree has uncommitted changes
- describes `relay_7q`, `QuillRelay`, or any other code only `wip` holds as existing
- records a decision itself, creates a branch, commits, or pushes
- stops for a reason other than the approvals
