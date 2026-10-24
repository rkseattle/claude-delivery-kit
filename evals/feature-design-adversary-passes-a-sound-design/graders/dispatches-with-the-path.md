---
type: tool_used
tool: Agent
input_match: '^(?=[\s\S]*"subagent_type"\s*:\s*"delivery-kit:feature-design-adversary")(?=[\s\S]*"prompt"\s*:\s*"/[^"\s]*/docs/design/per-endpoint-webhook-rate-limits\.md(?:\\n|\s)*")'
min: 1
---

The run dispatched the plugin's `feature-design-adversary` with the design doc's absolute
path as its whole prompt, as the agent's definition requires, rather than reviewing the
design itself or handing the agent a summary of it.
