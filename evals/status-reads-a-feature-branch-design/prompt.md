---
description: status, on a feature branch that alone holds an accepted design, reads the design at the branch's commit and reports it accepted with write-tickets next
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

/delivery-kit:status docs/design/sms-appointment-reminders.md

The workspace is a git repository with `feature/reminders` checked out. Jira is unavailable in
this environment, so do not call it.
