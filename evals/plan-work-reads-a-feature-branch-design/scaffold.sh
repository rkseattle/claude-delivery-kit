#!/usr/bin/env bash
# A git repo whose main holds no design, and a checked-out feature branch,
# feature/reminders, that commits an accepted design, so the design is on the branch alone.
# origin is a local bare clone of main, so a fetch succeeds offline.
# jira/ holds what jira_get_issue returns for Epic ABC-1 and its child ABC-2.
set -euo pipefail
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude docs/design src jira
printf 'docs/tickets/\n' > .gitignore
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src",
  "build_command": "python3 -m unittest discover -s src",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "brief_file": "none",
  "design_dir": "docs/design",
  "adr_dir": "docs/adr",
  "project_size": "small",
  "lifecycle_model": "iterative",
  "disciplines": []
}
JSON
cat > src/reminders.py <<'PY'
def due(appointments, now):
    """The appointments starting within the next 24 hours of now."""
    return [a for a in appointments if 0 <= (a["start"] - now).total_seconds() <= 86400]
PY
: > src/__init__.py
git add .gitignore .claude src
git commit -qm "Start the clinic project"
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
git switch -q -c feature/reminders
cat > docs/design/sms-appointment-reminders.md <<'MD'
---
status: accepted
date: 2026-11-01
decision-makers: lee
---

# SMS appointment reminders

## Summary

Epic: ABC-1

Text each patient an SMS reminder 24 hours before their appointment.

## Components and interfaces

- `src/reminders.py` `due(appointments, now)` picks the appointments to remind.
- A new `src/sms.py` `send(number, text)` sends one message through the SMS provider.

## Work plan

### Handoff: sms-reminders

- Send a reminder for each appointment `due` returns
  - Phase 1 — Add `sms.send` behind a provider interface
  - Phase 2 — Call it for each due appointment

## Decision

Approved by lee on 2026-11-01.
MD
cat > jira/ABC-1.json <<'JSON'
{"key": "ABC-1", "summary": "Send SMS appointment reminders", "issue_type": {"name": "Epic"},
 "status": {"name": "To Do", "category": "To Do"}, "labels": [], "issuelinks": [],
 "description": "## Goal\n\nPatients get a reminder before each appointment.\n\n## In scope\n\n- Design: `docs/design/sms-appointment-reminders.md`\n\n## Children\n\n- ABC-2"}
JSON
cat > jira/ABC-2.json <<'JSON'
{"key": "ABC-2", "summary": "Send an SMS reminder for each due appointment", "issue_type": {"name": "Story"},
 "status": {"name": "To Do", "category": "To Do"}, "labels": ["moscow-must", "sms-reminders"], "parent": {"key": "ABC-1"},
 "issuelinks": [],
 "description": "## Behavior\n\nEach appointment `due` returns gets one SMS through `sms.send`.\n\n## Acceptance criteria\n\n- AC1: `send` is called once per appointment `due` returns `[verify: ci @ src/test_reminders.py]`\n\n## Touch points\n\n- src/reminders.py (modify)\n- src/sms.py (create)"}
JSON
git add docs jira
git commit -qm "Record the SMS appointment reminders design"
