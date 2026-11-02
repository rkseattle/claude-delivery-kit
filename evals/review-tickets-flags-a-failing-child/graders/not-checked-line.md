---
type: regex
target: last_message
match: contains
pattern: 'Design\s*[—-]+\s*not checked:\s*the Epic names no design'
---

With `design_dir` set and no `- Design:` line in the Epic's In scope, the design section is
the one not-checked heading, giving that reason rather than `design_dir`'s, so the skill is
shown reading the Epic for its design.
