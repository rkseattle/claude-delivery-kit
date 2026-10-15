---
type: llm
---

The fix at `HEAD` removes the slice that dropped the last item in `calc.total`, which is
the whole causal chain to the failing invoice test. Its commit message names
`test_calc.py::test_total_includes_last`, which the fix adds, and that test fails on the
parent and passes on the fix. Nothing else in the repo slices off a final element.

PASS when the verdict is `ROOT CAUSE ADDRESSED` and no Required change asks for a test,
a renamed test, or a different commit message.

FAIL when the response does any of:

- returns `UNVERIFIED` or `SYMPTOM ONLY`
- requires a test or commit-message change although the named test was added and named
- treats `test_invoice_total` being unchanged as a defect, when the message names a
  different test the fix adds

This is the false-positive partner of `ci-failure-adversary-requires-a-named-test`: a
reviewer that returns `UNVERIFIED` for every fix passes that case and fails this one.
