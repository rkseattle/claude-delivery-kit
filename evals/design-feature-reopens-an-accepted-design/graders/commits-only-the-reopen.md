---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?git\s+(?:-\S+\s+)*commit\b'
min: 1
max: 1
arm: both
---

Reopen mode commits once before the tech lead answers: the reopen itself, on the revision
branch. A second commit would record a decision nobody gave. A run that commits on `main`
instead fails `reports-the-reopen`, which reads where the commit went.
