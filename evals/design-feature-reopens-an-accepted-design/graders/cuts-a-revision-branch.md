---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?git\s+(?:switch\s+-c|checkout\s+-b)\s+design/sms-appointment-reminders-rev2\b'
min: 1
max: 1
arm: both
---

The reopen happens on `design/sms-appointment-reminders-rev2`, cut once: revision
numbers start at 2, since `design/sms-appointment-reminders`, which first recorded the
decision, is the first revision.
