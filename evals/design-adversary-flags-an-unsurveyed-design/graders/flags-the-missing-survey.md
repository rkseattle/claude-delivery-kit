---
type: llm
---

The plan's `Approach` adopts the ticket's per-file design and cites a source for each
piece — content addressing, Firestore's queued writes, TanStack Query's refetch on focus
— plus an in-repo precedent. It never names two or three real systems that solve the
whole problem it solves: two-way synchronization of a set of files with a remote that
both sides edit. Systems that do — git's fetch, merge-base and three-way merge, Dropbox,
Syncthing, CRDT-based editors — each either detects concurrent edits or merges them, and
none lets one side's queued write silently discard the other's, as the plan's "queued
write wins" does.

`design-adversary.md` reports an `Approach` with no survey of the whole problem as a
MAJOR, cited against `Approach` rather than code, and defines BLOCKER as exactly five
things, none of which this is.

PASS when the response reports, as a MAJOR, that the approach was not checked against how
real systems solve the whole sync problem — for example by naming git's model, a
three-way merge, or another real sync system the plan should have surveyed — rather than
only faulting individual components.

FAIL when the response does any of:

- raises no finding about the missing survey of the whole problem
- files that finding as MINOR, UNVERIFIABLE, or BLOCKER — the severity is defined, and
  promoting it is the failure `design-adversary-passes-a-sound-plan` guards against
- accepts the per-component citations as satisfying the external-standard check
- criticizes individual pieces (the offline queue, the sha cache) without saying the
  design as a whole was never compared with real sync systems

A response that finds only the lost-update symptom has caught one consequence and missed
the cause this case exists to detect.
