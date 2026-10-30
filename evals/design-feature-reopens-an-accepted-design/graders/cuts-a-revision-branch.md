---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?git\s+(?:switch\s+-c|checkout\s+-b)\s+design/sms-appointment-reminders-rev2\b'
min: 1
max: 1
arm: both
---

The reopen happens on `design/sms-appointment-reminders-rev2`, the first free revision
branch, cut once. The scaffold's `design/sms-appointment-reminders` branch, which first
recorded the decision, already exists, so revision 1 is never cut.
