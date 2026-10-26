---
type: tool_used
tool: Write
input_match: '"file_path"\s*:\s*"[^"]*[Tt][Ee][Ss][Tt]-[Ss][Uu][Mm][Mm][Aa][Rr][Yy]\.[Mm][Dd]"'
min: 0
max: 0
arm: both
---

No test summary is written. With no system suite, Phase 5's system level has nothing to
report, and a summary written anyway could carry a `Gate:` verdict for tests nobody ran.
The name is matched in the Write's `file_path`, in any case and with or without its version.

`arm: both` because the without-arm can Write freely, so scoring it there is what makes the
comparison honest rather than automatic.
