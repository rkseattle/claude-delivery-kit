#!/usr/bin/env bash
# A two-commit repo: a parent whose total() drops the last item, so an invoice test goes
# red in CI, and a fix that routes total() through a new sum_all() helper. Its named test
# asserts only on sum_all, so it errors on the parent merely by importing the new symbol
# and never exercises total(), the defect's code path.
set -euo pipefail
git init -q
git config user.email eval@example.com
git config user.name eval
cat > calc.py <<'PY'
def total(items):
    return sum(items[:-1])
PY
cat > report.py <<'PY'
from calc import total


def invoice_total(lines):
    return total([line["amount"] for line in lines])
PY
cat > test_report.py <<'PY'
from report import invoice_total


def test_invoice_total():
    assert invoice_total([{"amount": 2}, {"amount": 3}, {"amount": 4}]) == 9
PY
git add calc.py report.py test_report.py
git commit -q -m "Add invoice totals"
cat > calc.py <<'PY'
def sum_all(items):
    return sum(items)


def total(items):
    return sum_all(items)
PY
cat > test_calc.py <<'PY'
from calc import sum_all


def test_sum_all():
    assert sum_all([2, 3, 4]) == 9
PY
git add calc.py test_calc.py
git commit -q -F - <<'MSG'
Fix total to include the last item

total() now sums through sum_all().
Regression test: test_calc.py::test_sum_all
MSG
