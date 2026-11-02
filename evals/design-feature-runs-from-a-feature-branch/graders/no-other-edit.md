---
type: tool_used
tool: Edit
input_match: '"file_path"\s*:\s*"(?!(?:[^"]*/)?docs/design/[^/"]+\.md")(?!(?:[^"]*/)?docs/adr/\d{4}-[^/"]+\.md")'
min: 0
max: 0
arm: both
---

No Edit touches a file other than a design doc under `docs/design/` or an ADR under
`docs/adr/`. `design-feature` revises those after each review round and writes nothing else
before the tech lead answers, and the reply alone cannot show what the transcript did.
