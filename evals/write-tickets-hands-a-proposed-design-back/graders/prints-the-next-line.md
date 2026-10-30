---
type: regex
target: last_message
match: contains
pattern: 'NEXT: /delivery-kit:design-feature (?:ABC-1|docs/design/sms-appointment-reminders\.md)'
arm: both
---

The reply hands the run to `design-feature` with the exact command, so the person running
the session never has to work out which skill owns the next step.
