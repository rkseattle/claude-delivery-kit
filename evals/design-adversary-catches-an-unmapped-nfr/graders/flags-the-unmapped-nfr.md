---
type: llm
---

ABC-219 carries two non-functional requirements. Both have a row in the plan's acceptance
criteria coverage table and a phase that delivers them. The plan's `NFR coverage` table
maps only **NFR1** (p95 under 300 ms) to a design element. **NFR2 — a response body of at
most 256 KB per page** — has no `NFR coverage` row, so the plan never says which design
element meets it.

`design-adversary.md` lists an NFR line in a covering ticket with no `NFR coverage` row
among the kinds of BLOCKER.

PASS when the response reports, under BLOCKER, that NFR2 (the 256 KB response-body limit)
has no `NFR coverage` row or no design element addressing it.

FAIL when the response does any of:

- does not mention NFR2 at all
- mentions it only as MAJOR, MINOR, or UNVERIFIABLE
- accepts the AC-table row and its phase as covering NFR2, without the design-element
  mapping
- describes the gap as a possible omission or asks whether it was intentional, rather than
  reporting it as a defect

Other findings, at any severity, do not affect the grade. A response that also blocks on
something else is graded only on whether NFR2 appears as a BLOCKER.
