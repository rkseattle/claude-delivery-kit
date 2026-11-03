---
description: review-tickets, on an Epic whose children all pass and that names no design, reports every ticket PASS, the design not checked with no verdict, and changes nothing
max_turns: 40
timeout_seconds: 900
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Agent
tags:
  - read-only
  - false-positive
---

/delivery-kit:review-tickets ABC-1

The workspace is a git repository with `main` checked out. Jira is unavailable in this
environment, so do not call it: `jira/ABC-1.json`, `jira/ABC-2.json`, and
`jira/ABC-3.json` hold what `jira_get_issue` returns for each key, and
`jira/search-parent-ABC-1.json` what `jira_search` returns for `parent = ABC-1`. Read them
in place of those calls.
