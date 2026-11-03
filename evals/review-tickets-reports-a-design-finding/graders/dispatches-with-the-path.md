---
type: tool_used
tool: Agent
input_match: '^(?=[\s\S]*"subagent_type"\s*:\s*"delivery-kit:feature-design-adversary")(?=[\s\S]*"prompt"\s*:\s*"/[^"\s]*/\.git/review-tickets-base-[^/"\s]+/docs/design/per-endpoint-webhook-rate-limits\.md(?:\\n|\s)*")'
min: 1
arm: with
---

The run dispatched `feature-design-adversary` with the design doc's absolute path as its
whole prompt, as the agent's definition requires, and that path is inside the review's own
base tree, `.git/review-tickets-base-*/`, not the checkout's copy.
