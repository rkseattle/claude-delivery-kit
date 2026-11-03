---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?lint_draft\.py\\?["'']?\s+\\?["'']?/[^"\s\\]*/\.git/review-tickets/draft\.md(?:\\"|'')?\s+--repo\b'
min: 1
arm: with
---

The run linted the draft under the git directory with `--repo`, so the lint findings the
report counts come from write-tickets' linter, not from `ticket-adversary` alone.
