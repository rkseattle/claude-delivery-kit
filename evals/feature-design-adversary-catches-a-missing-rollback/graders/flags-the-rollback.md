---
type: llm
---

The design's `## Rollout and rollback` section has four numbered steps. Steps 1, 2, and 4
each name the rollback step that undoes them. Step 3 — turning on `endpoint_rate_limits`
for the five internal test endpoints — names none. `gates/design-exit.md` says a rollout
step with no rollback step fails, and BLOCKER kind 5 of `agents/feature-design-adversary.md`
is exactly that.

PASS when the response reports, as a BLOCKER, that rollout step 3 of `Rollout and
rollback` names no rollback step.

FAIL when the response does any of:

- does not mention step 3's missing rollback at all
- reports it only as MAJOR, MINOR, or UNVERIFIABLE
- asks whether the omission was intentional, or treats step 4's rollback as covering
  step 3, rather than reporting the defect
- is not a review of the design, such as a reply that the agent could not be dispatched

Other findings do not affect this grader. Whether the reviewer blocks a sound design is
what `feature-design-adversary-passes-a-sound-design` checks.
