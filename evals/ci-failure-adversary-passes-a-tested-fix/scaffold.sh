#!/usr/bin/env bash
# A two-commit repo: a parent whose total() drops the last item, so an invoice test goes
# red in CI, and a sound fix that corrects total() and adds a unit test its message names.
# The test fails its assertion on the parent and passes on the fix, so nothing is a defect.
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
def total(items):
    return sum(items)
PY
cat > test_calc.py <<'PY'
from calc import total


def test_total_includes_last():
    assert total([2, 3, 4]) == 9


def test_total_of_one_item():
    assert total([5]) == 5
PY
git add calc.py test_calc.py
git commit -q -F - <<'MSG'
Fix total to include the last item

total() sliced off the final element, so every invoice dropped its last line.
Regression test: test_calc.py::test_total_includes_last
MSG
# Untracked, so none of the files below is part of the fix's diff.
mkdir -p .claude
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": ".",
  "build_command": "python3 -c 'import calc'",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection"
}
JSON
mkdir -p .claude/agent-rules
cat > .claude/agent-rules/ci-failure-adversary.md <<'RULES'
# ci-failure-adversary rules

- Tests are plain Python functions, and pytest is not installed. Run one with
  `python3 -c 'import <module>; <module>.<test>()'`.
RULES
