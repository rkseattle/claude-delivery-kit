---
type: llm
---

The project has `data-ml` in its `disciplines`. The plan's `Data ownership` is a table with
only `Store` and `Owning module` columns, and it lists the `churn_training` snapshots, a
dataset, with no schema owner and no version location.

`design-adversary.md`'s Design sections bullet makes this a MAJOR: with `data-ml`, a
`Data ownership` table missing the `Schema owner` or `Version location` column or cell.

PASS when the response reports the missing schema owner or version location for the
`churn_training` dataset, or the missing columns, as a MAJOR.

FAIL when the response does any of:

- does not mention the `Data ownership` table's missing schema owner or version location
- reports it only as MINOR or UNVERIFIABLE
- reports it as a BLOCKER, since BLOCKER is exactly five kinds and this is none of them
- asks whether the omission was intentional rather than reporting it as a defect

Other findings, at any severity, do not affect the grade.
