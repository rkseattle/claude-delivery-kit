---
description: plan-work, on a feature branch that alone holds the accepted design its ticket's Epic names, reads that design at the branch's commit and plans against it
max_turns: 40
timeout_seconds: 900
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Agent
  - WebSearch
  - WebFetch
  - Skill
tags:
  - lifecycle
  - feature-branch
---

/delivery-kit:plan-work ABC-2

The workspace is a git repository with `feature/reminders` checked out. Jira is unavailable in
this environment, so do not call it: `jira/ABC-1.json` and `jira/ABC-2.json` hold what
`jira_get_issue` returns for each key. Read them in place of those calls.
