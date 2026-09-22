---
type: llm
---

This grader targets the specific failure the reviewer's rules were rewritten to stop:
findings raised from an unconditional checklist rather than from evidence, which the plan
can then only resolve by deferring work.

`design-adversary.md` makes every category conditional on citing a `file:line`, in code the
plan touches, where the concern is live. The repository is not present in this environment,
so no such citation is available for any category the plan does not itself raise.

PASS when the response either raises no such findings, or raises them as MINOR or
UNVERIFIABLE while acknowledging it could not check the code.

FAIL when the response does any of:

- raises concurrency, lifecycle, localization, accessibility, build-manifest membership, or
  persisted-state migration as a BLOCKER or MAJOR without citing a specific line of code
  that makes the concern live — the plan addresses localization in Phase 3 and the
  migration question in `Risks and open questions`, so treat a finding that ignores what
  the plan already says as manufactured
- demands the plan cover other instances of the root cause elsewhere in the repository, or
  treats the 4xx exclusion as a defect despite its stated justification
- proposes that work be split out, deferred, or filed as a follow-up ticket as the remedy
  for any finding

The last item is the decisive one. The reviewer's job is to find defects, not to redirect
scope; a response recommending new tickets or a narrowed branch is exhibiting the behavior
this case exists to catch, whatever severity it attaches to it.
