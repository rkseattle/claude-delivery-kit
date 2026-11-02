---
type: regex
target: last_message
match: contains
pattern: 'NEXT: /delivery-kit:write-tickets (?=[^\n]*\bABC-1\b)(?=[^\n]*\bABC-3\b)'
---

The report hands the failing tickets to `write-tickets` with the exact command, naming
ABC-1 and ABC-3. ABC-2 may join them when `ticket-adversary` finds a MAJOR in it, so the
pattern requires the two linter failures, not the whole list.
