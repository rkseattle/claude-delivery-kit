---
type: llm
---

ABC-207 carries four acceptance criteria. The plan's coverage table lists three: the CSV
export, the 90-day window, and the column order. The fourth — **exporting is rate limited
to once per minute per user** — appears nowhere in the table, in any phase, or anywhere
else in the plan. No phase delivers it and no `Deviation` row explains its absence.

This is the first item in `design-adversary.md`'s definition of BLOCKER: an acceptance
criterion in a covering ticket with no phase that delivers it.

PASS when the response identifies the missing rate-limiting criterion **and** reports it as
a BLOCKER.

FAIL when the response does any of:

- does not mention the rate-limiting criterion at all
- mentions it only as MAJOR, MINOR, or UNVERIFIABLE
- describes it as a possible omission or asks whether it was intentional, rather than
  reporting it as a defect

The severity is the point of this case. The BLOCKER definition was narrowed to three
things, and this case exists to confirm the narrowing did not cost the reviewer the
findings it was always supposed to catch. A response that spots the gap but files it as a
MINOR has failed in the way this case was written to detect.
