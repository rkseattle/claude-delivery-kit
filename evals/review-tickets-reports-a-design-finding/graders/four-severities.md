---
type: regex
target: last_message
match: contains
pattern: '##\s*Design\s*[—-]+\s*`?docs/design/per-endpoint-webhook-rate-limits\.md`?(?=[\s\S]*\bBLOCKER\b)(?=[\s\S]*\bMAJOR\b)(?=[\s\S]*\bMINOR\b)(?=[\s\S]*\bUNVERIFIABLE\b)'
---

The design section opens with the checked heading naming the reviewed path, and carries
the reviewer's four severities, BLOCKER, MAJOR, MINOR, and UNVERIFIABLE, with `none` under
an empty one rather than the heading left out.
