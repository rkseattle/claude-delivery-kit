---
type: llm
---

The delivery workflow is five stages gated by an approval step after planning, with two
unconditional gates: the Definition of Done before every commit, and the pre-push
checklist before every push.

PASS when the response shows knowledge of that structure — for example by naming the
stages it would run, naming either gate, or stating that it stops because the project
configuration needed to run them is missing. Stopping early for a missing
`project.json` is a PASS: the workflow requires that file, so refusing without it is
correct behavior, not a failure to know the workflow.

FAIL when the response invents a different workflow, proceeds through stages as though
configured when it is not, or describes the gates as optional.
