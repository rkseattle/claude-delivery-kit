---
description: design-feature reopens a design already accepted on main on a design/<slug>-rev<N> branch, recording why, and never edits main
max_turns: 60
timeout_seconds: 1800
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Skill
  - Agent
tags:
  - guardrail
  - lifecycle
---

/delivery-kit:design-feature docs/design/sms-appointment-reminders.md

The workspace is a git repository with `main` checked out. `write-tickets` stopped at its
review cap on this design, and its draft is `docs/tickets/sms-appointment-reminders.md`.
Web search and Jira are unavailable in this environment, so do not call either; the
design's `## Survey` already holds its sources, so treat them as retrieved.

No engineer outside the immediate team will review this design; the workspace's exceptions
log records that.
