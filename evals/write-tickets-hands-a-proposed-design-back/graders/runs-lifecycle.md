---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?project_rules\.py\\?"?\s+lifecycle\b'
min: 1
arm: with
---

`write-tickets` asks `project_rules.py lifecycle` where the design stands rather than
reasoning about its status from whichever file it read last, which is how the incident
this case comes from gave three contradictory directions in one session.
