---
type: regex
target: last_message
pattern: "AC1\\b"
---

The acceptance-criteria coverage carries stable `AC<n>` identifiers. Every later status
report names criteria by these IDs, so a plan without them produces reports that cannot
reference anything checkable.
