---
type: llm
---

The fix at `HEAD` changes `calc.py`, executable code, and answers a CI failure, so it is a
defect fix under the Definition of Done's defect-fix gate. Its commit message, "Fix total
to include the last item", names no test. The agent definition makes that `UNVERIFIED`
whatever the causal chain shows, with the missing test as the first Required change.

PASS when the verdict is `UNVERIFIED` **and** the response attributes it to the commit
message naming no test, or says the message must name `test_total_includes_last`.

FAIL when the response does any of:

- returns `ROOT CAUSE ADDRESSED` or `SYMPTOM ONLY`
- returns `UNVERIFIED` only for another reason, never mentioning the unnamed test
- asks for a new test to be written while never saying the commit message must name one

The source change itself is correct, which is the point: a reviewer judging the code alone
passes it, and this case exists to confirm the defect-fix gate still decides the verdict.
