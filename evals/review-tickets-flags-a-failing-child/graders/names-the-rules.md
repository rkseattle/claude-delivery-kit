---
type: llm
---

The linter, run on the draft `review-tickets` builds from `jira/`, prints exactly two
counted errors: `ERROR ABC-1 [E3] child ABC-3 maps to no success measure and is not
'enabling'` and `ERROR ABC-3 [R12] missing Priority: — one of Must, Should, Could, Won't`.
It also prints `[R2] missing Handoff label` for ABC-2 and ABC-3, which the skill reports as
unknown and counts for nothing, since Jira marks no label as a handoff.

PASS when the response reports, each as a finding with its rule ID:

- `E3` in the ABC-1 section, naming ABC-3 and quoting or paraphrasing the unmapped child
- `R12` in the ABC-3 section, naming the missing priority

and reports ABC-1 and ABC-3 as FAIL.

FAIL when the response does any of:

- reports either finding without its rule ID, or under the other ticket
- reports either as a warning, or as unknown
- counts an `R2` handoff line as a failure
