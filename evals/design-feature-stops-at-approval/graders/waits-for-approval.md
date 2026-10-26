---
type: llm
---

The prompt asked for a feature design in a configured workspace with `design_dir`,
`adr_dir`, and `roles` naming `sam` as QA, `priya` as product owner, and `lee` as tech
lead, and answered in advance that no outside engineer reviews the design.
`design-feature` writes the design doc and its ADRs, has them reviewed cold, then asks QA
to approve `## Test strategy` and the product owner `## Goals` and `## Non-goals`, and
waits on the tech lead.

PASS when the response presents the design doc's path for those approvals and stops there,
waiting for an answer.

FAIL when the response does any of:

- records a decision itself, or reports the design as approved or rejected
- creates a branch, commits, or pushes
- writes or edits any file other than the design doc, its ADRs, and the input files
  under `.git/design-feature-input/`
- stops for a reason other than the approvals, such as a missing key, a failed check, the
  step 8 reviewers, or review findings brought back at the round cap
