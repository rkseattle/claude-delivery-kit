---
type: tool_used
tool: Read
input_match: "(project\\.json|SKILL\\.md|definition-of-done|pre-push|status-report|invariants)"
min: 1
arm: both
---

A configuration file, stage file, or gate is read from disk.

`deliver` opens by reading `project.json`, and reads each stage's `SKILL.md` on arrival
rather than working from memory — a run that consults nothing is following a remembered
approximation of the workflow instead of the workflow.

`arm: both` because the without-arm can read files too. It has no stage files to find,
which is the asymmetry this measures: the with-arm should reach for them and find them,
the without-arm has nothing to reach for.
