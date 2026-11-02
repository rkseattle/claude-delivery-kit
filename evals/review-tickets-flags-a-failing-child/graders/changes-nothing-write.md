---
type: tool_used
tool: Write
input_match: '"file_path"\s*:\s*"(?![^"]*/\.git/review-tickets(?:-input)?/[^/"]+")'
min: 0
max: 0
arm: both
---

Every file the run writes is its own, under `.git/review-tickets/` or
`.git/review-tickets-input/`, outside the work tree, so `git status` is unchanged.
