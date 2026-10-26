---
type: file_exists
path: docs/design/*.md
arm: both
---

The run created a design doc under `design_dir`, read from the workspace after the run
rather than from the transcript. `writes-the-design` checks the Write call; this checks
the file it should have left.
