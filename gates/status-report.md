# Status report — required at every phase and stage boundary

Used by `implement-phases` at every phase boundary, and by `branch-review`, `ship-pr`, and
`ci-green` at every stage boundary, scaled to what that stage does — a stage that fixes
review findings still says which files it touched, how long it ran, and which ACs it moved.

Report before starting the next phase — every phase, including the last one, and including
a phase that changed one line. This is not a summary of the work; it is where Rob sees
where the run is and what it cost. Then move directly on without pausing for a reply.

A boundary crossed without a report is the most common way a run becomes unreviewable: the
information exists only while the phase is fresh, and reconstructing it afterward from
`git log` loses the timing entirely.

Five parts, in this order. Friction is recorded, not reported — see the last section.

## 1. The heading

`Phase <n> of <total> complete — <phase name>`.

## 2. The phase table

Every phase in the plan, not just the finished ones, so remaining work is visible without
scrolling back:

```
| Phase | Status | Duration | Files |
|---|---|---|---|
| 1 Cache eviction policy | done | 18m | 4 |
| 2 Settings control | done | 6m | 3 |
| 3 Unit tests | done | 41m | 7 |
| 4 Localization | pending | — | — |
```

Duration is `finished_at - started_at` from `.claude/state/current-plan.json`, rounded to
the minute — never an estimate. It is wall-clock, so it includes time spent waiting on a
review round or a test run; that is the number worth knowing. A phase whose timestamps are
missing reports `unknown`.

## 3. Files modified this phase

The full list from `git show --stat --name-only <commit>`, with the commit SHA — never from
memory of what you edited, which misses build manifests, generated files, and whatever a
lint autofix touched. Not a count, not "and 4 others": the list is what makes a wrong-file
mistake visible while it is still one commit from the top. Group by workspace when it runs
past a dozen.

## 4. Acceptance criteria

Every AC on the covered tickets, with its state after this phase. All of them every time,
not just the ones that moved:

```
| AC | Criterion | Met | Evidence |
|---|---|---|---|
| AC1 | Cache expires after 24h | yes | CacheTests.testExpiry |
| AC2 | Expiry configurable in settings | yes | SettingsView:142, SettingsTests.testTTL |
| AC3 | Works offline with a warm cache | no | out-of-band tier, not yet run — phase 5 |
```

`met` is `yes` only with evidence in the row, and the evidence must name something that
fails if the behavior regresses — code existing that ought to satisfy it is not evidence. A
test name, a specific assertion, a gate that now passes. Never mark an AC met because the
phase "addressed" it.

**An AC whose `verified_by` names an out-of-band tier says so and stays `no` until that
verification runs.** A green automated suite is silent on exactly that behavior, so an AC
backed only by unit tests of its underlying math is not met — the math is tested, the
behavior is not. Say which one the evidence covers.

An AC that no phase has touched shows `no` and says which phase is meant to cover it. An AC
the plan does not cover anywhere is the report's most useful output: call it out explicitly
rather than letting it sit unremarked in the table. That is a plan gap, and it is cheapest
to find now.

## 5. Gates

One line naming what ran and what came back, with the counts read from the result file —
`passed/total/failed/skipped`. Never a console summary. `commit-adversary` gets its round
count and the verdict that ended it.

## Citations — recorded, not reported

Append every design decision's external standard to `citations[]` — the decision, the
standard it is an instance of, how it was applied here — and print nothing about it here.
Record it at the decision: which standard shaped a choice is exactly what `git log` cannot
say afterward. `ci-green` reports the list once, deduplicated, so a standard applied across
four phases reads as one entry.

## Friction — recorded, not reported

**Do not print a friction section in this report.** Append each item to `friction[]` in
`.claude/state/current-plan.json` and say nothing further about it here. The whole list
reports once, at the end of delivery, from `ci-green` — per `deliver`'s invariant on process
feedback, which says why one end-of-run list beats four per-stage ones.

Record an item the moment you notice it. Noticing afterward does not work: by then the cost
is invisible.

```json
{ "stage": "implement-phases", "phase": 3, "phase_name": "E2E specs",
  "at": "2026-09-10T16:52:35Z",
  "item": "<what cost time>", "target_file": "gates/definition-of-done.md",
  "proposed_wording": "<the exact text>", "displaces": "<what comes out, or nothing>" }
```

`phase` and `phase_name` are the phase this arose in; both are `null` outside
`implement-phases`, and `ci-green` adds `iteration` instead. Provenance is what makes the
end-of-run list readable — an item hit in three separate phases is a different signal from
one hit once, and the dedup keeps every origin rather than collapsing them.

The bar is **repeatable and preventable**. A gate that failed on something no written rule
covers qualifies; a typo does not. So does a rule that exists but was not found from where
you were reading — that is a cross-reference problem and names its own fix.

**A friction item names what it would replace, or states that it adds nothing.** The most
common resolution is not a new rule: it is moving an existing one to where you were actually
reading, narrowing one that fired wrongly, or deleting one that sent you the wrong way.
Those are the valuable items — they leave the corpus the same size or smaller. An item
proposing genuinely new text says what it displaces, per `deliver`'s line-budget invariant.
An item whose fix belongs in the shared plugin rather than a project file says so, per
`deliver`'s **Shared before project**.

Record nothing when the phase genuinely ran clean, and do not treat an empty `friction[]` as
a section you failed to fill. An item whose honest answer is "nothing to change, this was a
one-off" is not a friction item — an invented one is worse than an empty list, because a
list of real friction is only useful if everything on it is real.

Never apply the fix. Phases record; `ci-green` proposes; Rob decides.
