#!/usr/bin/env bash
# A git repo whose main holds no design, and a checked-out feature branch,
# feature/reminders, that commits an accepted design, so the design is on the branch alone.
# origin is a local bare clone of main, so a fetch succeeds offline.
set -euo pipefail
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude docs/design src
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
git add docs
git commit -qm "Record the SMS appointment reminders design"
