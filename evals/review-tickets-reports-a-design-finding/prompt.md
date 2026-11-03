---
description: review-tickets, on an Epic whose In scope names an accepted design with a rollout step that has no rollback, delegates the design's path alone to feature-design-adversary, reports its BLOCKER in a design section apart from the tickets, and hands it to design-feature
max_turns: 50
timeout_seconds: 1200
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Agent
  - WebSearch
  - WebFetch
tags:
  - read-only
  - regression
---

/delivery-kit:review-tickets ABC-1

The workspace is a git repository with `main` checked out. Jira is unavailable in this
environment, so do not call it: `jira/ABC-1.json` and `jira/ABC-2.json` hold what
`jira_get_issue` returns for each key, and `jira/search-parent-ABC-1.json` what
`jira_search` returns for `parent = ABC-1`. Read them in place of those calls.
