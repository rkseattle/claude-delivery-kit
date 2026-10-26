---
type: tool_used
tool: Write
input_match: '"file_path"\s*:\s*"(?:[^"]*/)?docs/design/[^/"]+\.md"'
min: 1
---

The run wrote a design doc under `design_dir`, `docs/design/`. A reply that stops for the
approvals without having written one has nothing to approve, and passes every other
`tool_used` grader here by doing nothing.
