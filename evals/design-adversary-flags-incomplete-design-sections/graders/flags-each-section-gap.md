---
type: llm
---

The plan carries every design section, every acceptance criterion and ticket NFR has a row
and a phase, and every NFR has an `NFR coverage` row. Seven entries inside those sections are incomplete:

1. `DeliveryHistoryQuery` has no `Versioning` line.
2. `DeliveryExport` has no `Errors` line.
3. The `Likely changes` entry ("the export format may change later") names no interface
   that hides the decision.
4. The `NFR coverage` row for NFR1 ("should be fast enough once streaming is in place")
   names no module from `Components and interfaces`.
5. Phase 2 adds the `zip_kit` gem, a new external dependency the flowchart does not show.
6. `DeliveriesController#export` has no `Layer` line.
7. `DeliveryExport`'s `Layer` line names two layers, presentation and data access.

`design-adversary.md` makes each of these a MAJOR cited against its plan section, exempt
from the rule that a finding must cite code. None is a BLOCKER.

The parent Epic's NFR has an `NFR coverage` row reading `untouched — <reason>`, which the
plan template allows and `design-adversary.md` exempts. It is not a defect.

PASS when the response reports every one of the seven as a MAJOR, reports none of them as a
BLOCKER, and raises no finding against ABC-230's `untouched` row.

FAIL when the response does any of:

- omits any of the seven, or reports one only as MINOR or UNVERIFIABLE
- raises a finding, at any severity, against ABC-230's `untouched` row
- reports any of the seven as a BLOCKER
- drops a finding because it cannot cite a line of code for it

Other findings, at any severity, do not affect the grade.
