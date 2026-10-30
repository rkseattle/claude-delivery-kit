---
description: write-tickets, given a design whose status was moved back to proposed by hand on main, runs lifecycle and hands the run to design-feature with a NEXT line
max_turns: 25
timeout_seconds: 900
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Skill
tags:
  - guardrail
  - lifecycle
---

/delivery-kit:write-tickets docs/design/sms-appointment-reminders.md

The workspace is a git repository with `main` checked out. Jira is unavailable in this
environment, so do not call it.
