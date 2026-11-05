---
description: write-tickets, on a feature branch that alone holds an accepted design, reads the design at the branch's commit and slices its work plan rather than handing the run back to design-feature
max_turns: 30
timeout_seconds: 900
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Skill
tags:
  - lifecycle
  - feature-branch
---

/delivery-kit:write-tickets docs/design/sms-appointment-reminders.md

The workspace is a git repository with `feature/reminders` checked out. Jira is unavailable in
this environment, so do not call it; there are no existing tickets to search.
