---
type: tool_used
tool: Write
input_match: "test-summary\\.md"
min: 0
max: 0
arm: both
---

No test summary is written. With no system suite, Phase 5's system level has nothing to
report, and a summary written anyway could carry a `Gate:` verdict for tests nobody ran.

`arm: both` because the without-arm can Write freely, so scoring it there is what makes the
comparison honest rather than automatic.
