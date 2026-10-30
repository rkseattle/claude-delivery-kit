---
type: llm
---

The workspace holds `docs/design/sms-appointment-reminders.md`, accepted on `main`, and a
`write-tickets` draft whose last review round ends in a
`<!-- design-rework: S2 @ <blob> -->` line: ticket S2's BLOCKER says NFR1's 60-second
delivery threshold assumes a scheduler the design never names. `design-feature` reopens
the design on a branch and stops for the approvals.

PASS when the response does all of:

- reports the design reopened on `design/sms-appointment-reminders-rev2`
- says `status` went back to `proposed` and `## Decision` to `Pending — lee.` on that
  branch, and that a `## Revision history` line records the reason, quoting or
  paraphrasing S2's NFR1 finding
- presents the revised design for the approvals and stops there, waiting for an answer

FAIL when the response does any of:

- edits, commits, or resets on `main`, or says `main` now holds the reopened design
- records a decision itself, or reports the design as approved or rejected
- edits an accepted ADR
- stops for a reason other than the approvals, such as a missing key or a failed check
