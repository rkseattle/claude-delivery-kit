---
type: llm
---

The workspace's accepted design `docs/design/sms-appointment-reminders.md` exists only on
the checked-out `feature/reminders` branch, not on `main`. `write-tickets` builds tickets
from an accepted design's `Work plan`.

PASS when the response works from the design's `sms-reminders` handoff: it drafts or
presents tickets from it, or stops later only for a reason unrelated to where the design
lives, such as Jira being unavailable.

FAIL when the response does any of:

- says the design does not exist, is not accepted, or must be merged to `main` first
- names `design-feature` as the next step
- tells the person to switch to `main` or merge the branch before running the skill
