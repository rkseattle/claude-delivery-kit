---
type: tool_used
tool: Agent
input_match: '^(?=[\s\S]*"subagent_type"\s*:\s*"delivery-kit:ticket-adversary")(?=[\s\S]*"prompt"\s*:\s*"/[^"\s]*/\.git/review-tickets/draft\.md(?:\\n|\s)*")'
min: 1
arm: with
---

The run dispatched `ticket-adversary` with the draft's absolute path as its whole prompt,
the draft under the git directory rather than anywhere `git status` would show it.
