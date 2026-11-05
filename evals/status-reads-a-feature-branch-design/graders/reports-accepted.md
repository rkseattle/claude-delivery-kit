---
type: regex
target: last_message
match: contains
pattern: 'design-accepted-on-parent docs/design/sms-appointment-reminders\.md'
arm: both
---

The reply reports the branch's accepted design, rather than a working-tree draft sent back
to `design-feature` because `main` lacks it.
