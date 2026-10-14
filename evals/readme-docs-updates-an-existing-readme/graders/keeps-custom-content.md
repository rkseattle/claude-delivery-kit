---
type: llm
---

The workspace README has a custom `## Benchmarks` section with real measurements, and
`CONTRIBUTING.md` links to it as `README.md#benchmarks`. Its `## Installing` and
`## Running it` headings are ones the template names differently.

PASS when the measurements survive — kept in the README, or moved to a file under `docs/`
that the README links to — **and** the `#benchmarks` anchor still resolves, or the reply
names that `CONTRIBUTING.md` link as broken by the change.

FAIL when the measurements are gone, or when the anchor no longer resolves and the reply
does not say so.
