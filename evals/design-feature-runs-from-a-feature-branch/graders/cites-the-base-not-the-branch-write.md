---
type: tool_used
tool: Write
input_match: '^(?=[^]*"file_path"\s*:\s*"(?:[^"]*/)?docs/(?:design/[^/"]+|adr/\d{4}-[^/"]+)\.md")[^]*"content"\s*:\s*"(?:[^"\\]|\\.)*?(?:relay_7q|QuillRelay)'
min: 0
max: 0
arm: both
---

No Write of the design doc or an ADR mentions `relay_7q` or `QuillRelay`. Both exist only in the
`wip` branch's unmerged commit, and no design would invent either name, so a design naming either read the working tree rather than
the base commit, `origin/main`, that its `## Current state` must describe.
