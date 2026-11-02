---
type: llm
---

Epic ABC-1 and Stories ABC-2 and ABC-3 meet the rubric: each Story has a `moscow-*`
label, a handoff label, one decided behavior change, concrete ACs whose `[verify:]`
evidence is a tracked test file, production touch points, out of scope, and dependencies,
and each maps to a success measure. The Epic names no
design. Jira marks no label as a handoff, so each Story's `R2` handoff line is reported
unknown and counts for nothing.

PASS when the response reports ABC-1, ABC-2, and ABC-3 each as PASS, says the design was
not checked, and gives the design no PASS or FAIL of its own.

FAIL when the response does any of:

- reports any of the three as FAIL, or counts an unknown handoff line against one
- reports the design as passing or failing, or counts it in the PASS/FAIL totals
- reviews a design it invented, or asks for one
- has no `NEXT: none` line, or names a `write-tickets` command
