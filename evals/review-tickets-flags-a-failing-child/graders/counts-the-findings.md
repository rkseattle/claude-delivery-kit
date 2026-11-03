---
type: regex
target: last_message
match: contains
pattern: '\|\s*`?ABC-1\b[^|\n]*\|\s*1\s*\|\s*0\s*\|[^\n]*\bFAIL\b[\s\S]*\|\s*`?ABC-2\b[^|\n]*\|\s*0\s*\|\s*0\s*\|[\s\S]*\|\s*`?ABC-3\b[^|\n]*\|\s*1\s*\|\s*0\s*\|[^\n]*\bFAIL\b'
---

The summary table's `Lint errors` and `Lint warnings` cells hold the linter's exact counts
per ticket, the two `R2` handoff lines set aside: ABC-1 one error (E3) and no warning,
ABC-2 none, ABC-3 one error (R12) and no warning, with ABC-1 and ABC-3 marked FAIL. The
linter is deterministic, so these counts are exact. `ticket-adversary`'s findings vary by
run, so no exact total of them can be asserted; `names-the-rules` grades them instead.
