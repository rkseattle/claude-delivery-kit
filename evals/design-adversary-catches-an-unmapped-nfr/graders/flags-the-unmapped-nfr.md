---
type: llm
---

ABC-219 carries two non-functional requirements. Both have a row in the plan's acceptance
criteria coverage table and a phase that delivers them. The plan's `NFR coverage` table
maps only **NFR1** (p95 under 300 ms) to a design element. **NFR2 — a response body of at
most 256 KB per page** — has no `NFR coverage` row, so the plan never says which design
element meets it.

Its parent Epic, ABC-218, carries two more. **NFR1 — an API 5xx error rate below 0.1%** —
has no `NFR coverage` row, neither a design element nor an `untouched` reason. **NFR2 — API
p99 under 1 second for list endpoints** — has a row naming `Api::DeliveriesController#index`,
so the branch affects it, but it has no AC-table row and no phase delivers or verifies it.

`design-adversary.md` makes each of these a BLOCKER: an NFR with no `NFR coverage` row,
and a parent-Epic NFR whose row is not `untouched` with no phase that delivers it.

PASS when the response reports all three under BLOCKER: ABC-219's NFR2 (the 256 KB
response-body limit) and ABC-218's NFR1 (the 5xx error rate) as having no `NFR coverage`
row or no design element, and ABC-218's NFR2 (p99 under 1 second) as having no phase.

FAIL when the response does any of:

- omits any of the three NFRs
- mentions any of them only as MAJOR, MINOR, or UNVERIFIABLE
- accepts the AC-table row and its phase as covering NFR2, without the design-element
  mapping
- treats an Epic NFR as outside the review because it is not on the covering ticket
- describes any gap as a possible omission or asks whether it was intentional, rather
  than reporting it as a defect

Other findings, at any severity, do not affect the grade. A response that also blocks on
something else is graded only on whether all three NFRs appear as BLOCKERs.
