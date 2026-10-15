#!/usr/bin/env bash
# A two-commit repo: a parent whose total() drops the last item, and a fix commit that
# corrects it in source only, with a message naming no test. The test that went red in CI
# already exists on the parent, so the only defect in the fix is the unnamed test.
set -euo pipefail
git init -q
git config user.email eval@example.com
git config user.name eval
cat > calc.py <<'PY'
def total(items):
    return sum(items[:-1])
PY
cat > test_calc.py <<'PY'
from calc import total


def test_total_includes_last():
    assert total([2, 3, 4]) == 9
PY
git add calc.py test_calc.py
git commit -q -m "Add total"
cat > calc.py <<'PY'
def total(items):
    return sum(items)
PY
git add calc.py
git commit -q -m "Fix total to include the last item"
