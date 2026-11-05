---
type: llm
---

ABC-2's Epic ABC-1 names `docs/design/sms-appointment-reminders.md`, an accepted design that
exists only on the checked-out `feature/reminders` branch, not on `main`.

PASS when the plan or the reply weighs that design: it names its `sms.send` component or
its `sms-reminders` work plan, and does not stop over where the design lives.

FAIL when the response does any of:

- says the design is missing, not accepted, or must be merged to `main` first
- plans with no design, as if the Epic named none
- tells the person to switch to `main` or merge the branch before planning
