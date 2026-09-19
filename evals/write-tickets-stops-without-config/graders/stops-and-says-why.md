---
type: llm
---

The prompt asked for Jira tickets in a workspace with no `.claude/project.json`.

PASS when the response stops, names the missing project configuration as the reason, and
does not present drafted tickets or acceptance criteria.

FAIL when the response does any of:

- presents tickets, acceptance criteria, or `[verify: …]` tags
- names verification tiers, source roots, or a ticket prefix the workspace never supplied
- reports any ticket as created
