#!/usr/bin/env bash
# A git repo whose origin is a local bare clone, a project.json leaving design_dir, adr_dir,
# and brief_file out, ticket-adversary's rules file, and jira/, what jira_get_issue and
# jira_search return for Epic ABC-1 and its two children. Every ticket passes the linter;
# the Epic names no design.
set -euo pipefail
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude/agent-rules src tests jira
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src tests",
  "build_command": "python3 -m unittest discover -s tests -t .",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "disciplines": []
}
JSON
cat > .claude/agent-rules/ticket-adversary.md <<'RULES'
# ticket-adversary rules

- Jira is unreachable from this workspace. The draft holds every ticket under review, and
  each ticket's epic is in it. A claim only Jira could settle is a DECISION, never a
  BLOCKER or MAJOR.
RULES
cat > src/reminders.py <<'PY'
def due(appointments, now):
    """Each appointment whose "at", in epoch seconds, is at most 86400 seconds after now."""
    return [a for a in appointments if a["at"] - now <= 86400]
PY
cat > tests/test_reminders.py <<'PY'
import unittest

from src.reminders import due


class DueTests(unittest.TestCase):
    def test_an_appointment_an_hour_ahead_is_due(self):
        self.assertEqual(due([{"at": 3600}], 0), [{"at": 3600}])
PY
: > src/__init__.py
: > tests/__init__.py
cat > jira/ABC-1.json <<'JSON'
{"key": "ABC-1", "summary": "Remind patients of appointments by SMS", "issue_type": {"name": "Epic"},
 "status": {"name": "To Do", "category": "To Do"}, "labels": [], "issuelinks": [],
 "description": "## Goal\n\nFewer missed appointments: each patient gets an SMS reminder in the 24 hours before an appointment.\n\n## Success measures\n\n- SM1: only appointments in the next 24 hours are listed as due `[children: ABC-2]`\n- SM2: a due appointment's reminder text names its clinic and its time `[children: ABC-3]`\n\n## In scope\n\n- choosing who is due, and the reminder text\n\n## Out of scope\n\n- sending the SMS: the clinic's gateway does it, not planned here\n\n## Children\n\n- ABC-2\n- ABC-3"}
JSON
cat > jira/ABC-2.json <<'JSON'
{"key": "ABC-2", "summary": "Leave past appointments out of the due list", "issue_type": {"name": "Story"},
 "status": {"name": "To Do", "category": "To Do"}, "labels": ["moscow-must", "sms-reminders-pr-01"], "parent": {"key": "ABC-1"},
 "issuelinks": [],
 "description": "## Context\n\n`due(appointments, now)` returns every appointment at most 86400 seconds after `now`, past ones included, so a patient is texted about an appointment already over.\n\n## Behavior\n\n`due` returns only appointments whose `at` is at least `now` and at most 86400 seconds after it.\n\n## Acceptance criteria\n\n- AC1: with `now` 100 `due` leaves out an appointment whose `at` is 99 `[verify: ci @ tests/test_reminders.py]`\n- AC2: with `now` 100 `due` keeps an appointment whose `at` is 100 `[verify: ci @ tests/test_reminders.py]`\n- AC3: with `now` 100 `due` keeps an appointment whose `at` is 86500 `[verify: ci @ tests/test_reminders.py]`\n- AC4: with `now` 100 `due` leaves out an appointment whose `at` is 86501 `[verify: ci @ tests/test_reminders.py]`\n\n## Touch points\n\n- src/reminders.py (modify): `due` drops appointments before `now`\n\n## Out of scope\n\n- the reminder text: ABC-3\n\n## Dependencies\n\n- Code: `due()` in src/reminders.py (exists on the parent branch)"}
JSON
cat > jira/ABC-3.json <<'JSON'
{"key": "ABC-3", "summary": "Write the reminder text for an appointment", "issue_type": {"name": "Story"},
 "status": {"name": "To Do", "category": "To Do"}, "labels": ["moscow-should", "sms-reminders-pr-01"], "parent": {"key": "ABC-1"},
 "issuelinks": [],
 "description": "## Context\n\nAn appointment is a dict with `at`, in epoch seconds, and `clinic`, the clinic's name. Its reminder names both, with the time in the clinic's zone.\n\n## Behavior\n\n`reminder_text(appointment, zone)` returns `Reminder: <clinic> at <HH:MM>.` with `HH:MM` the 24-hour local time of `at` in `zone`, an IANA zone name read with `zoneinfo`.\n\n## Acceptance criteria\n\n- AC1: for clinic `Elm St` with `at` 1767346200 in zone `UTC` `reminder_text` returns `Reminder: Elm St at 09:30.` `[verify: ci @ tests/test_reminders.py]`\n- AC2: for clinic `Elm St` with `at` 1767346200 in zone `America/New_York` `reminder_text` returns `Reminder: Elm St at 04:30.` `[verify: ci @ tests/test_reminders.py]`\n\n## Touch points\n\n- src/reminders.py (modify): add `reminder_text`\n\n## Out of scope\n\n- translations of the text: not planned\n\n## Dependencies\n\n- Code: the `zoneinfo` module of the Python standard library (exists on the parent branch)"}
JSON
cat > jira/search-parent-ABC-1.json <<'JSON'
{"total": 2, "issues": [{"key": "ABC-2", "summary": "Leave past appointments out of the due list", "issue_type": {"name": "Story"}},
 {"key": "ABC-3", "summary": "Write the reminder text for an appointment", "issue_type": {"name": "Story"}}]}
JSON
git add .claude src tests jira
git commit -qm "Seed the SMS reminders project"
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
