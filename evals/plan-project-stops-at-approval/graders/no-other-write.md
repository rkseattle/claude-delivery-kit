---
type: tool_used
tool: Write
input_match: "\"file_path\"\\s*:\\s*\"(?![^\"]*docs/brief\\.md\")"
min: 0
max: 0
arm: both
---

No Write touches a file other than `docs/brief.md`. `plan-project` writes nothing but
`brief_file` before the sponsor answers, and the reply alone cannot show what the
transcript did.
