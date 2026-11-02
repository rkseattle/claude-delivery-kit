---
type: regex
target: last_message
match: contains
pattern: 'PASS:\s*3\s+FAIL:\s*0\b[\s\S]*NEXT: none'
---

The summary counts all three tickets as passing and the report ends with no `write-tickets`
command, so nothing is handed on to fix.
