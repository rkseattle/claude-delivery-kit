---
type: tool_used
tool: Edit
input_match: '^(?=[^]*"file_path"\s*:\s*"(?:[^"]*/)?docs/(?:design/[^/"]+|adr/\d{4}-[^/"]+)\.md")[^]*"new_string"\s*:\s*"(?:[^"\\]|\\.)*?(?:relay_7q|QuillRelay)'
min: 0
max: 0
arm: both
---

No Edit of the design doc or an ADR adds `relay_7q` or `QuillRelay`, for the reason
`cites-the-base-not-the-branch-write` gives: both exist only on the unmerged `wip` branch.
