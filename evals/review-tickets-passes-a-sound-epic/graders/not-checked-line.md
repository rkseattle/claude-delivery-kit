---
type: regex
target: last_message
match: contains
pattern: 'Design\s*[—-]+\s*not checked:\s*`?design_dir`? is `?(?:unset|none)'
---

With `design_dir` left out of project.json, the design section is the one not-checked
heading, giving the first reason that applies, rather than a design verdict.
