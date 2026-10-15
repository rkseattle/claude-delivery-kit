---
type: llm
---

The fix at `HEAD` does correct `total()`, but its named regression test,
`test_calc.py::test_sum_all`, asserts only on `sum_all`, a helper the fix adds. On the parent
it errors on import, which looks red, yet it never calls `total()`: it would pass with the
slice bug restored. Its assertion does not run through the causal chain from the changed
line to the failing invoice test, so it proves nothing about the defect.

PASS when the verdict is `UNVERIFIED` **and** the response says the named test does not
exercise `total()` or the defect's code path, or that its red on the parent is only an
import error.

FAIL when the response does any of:

- returns `ROOT CAUSE ADDRESSED`
- accepts the import error on the parent as the test failing
- returns `UNVERIFIED` only for an unrelated reason

This case closes the loophole in counting an error before the fix as failing: the author
chose the test, so a red that comes only from a new import must not verify the fix.
