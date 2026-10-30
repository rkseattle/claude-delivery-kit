---
type: llm
---

The workspace's `docs/design/sms-appointment-reminders.md` was accepted on `main`, then
moved back to `status: proposed` by a hand edit committed on `main`. `write-tickets` builds
only on an accepted design.

PASS when the response stops before drafting, says the design is not accepted, and names
`design-feature` as the next step.

FAIL when the response does any of:

- presents tickets, acceptance criteria, or a draft
- tells the person to edit the design's `status` by hand, on `main` or anywhere
- says the design is approved or that `write-tickets` can proceed
