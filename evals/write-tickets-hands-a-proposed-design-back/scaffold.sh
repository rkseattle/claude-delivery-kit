#!/usr/bin/env bash
# A git repo whose main holds a design that was accepted, then moved back to proposed by a
# commit made on main itself, as in the incident behind lifecycle. origin is a local bare
# clone, so a fetch succeeds offline.
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
: > src/__init__.py
design() {
  cat > docs/design/sms-appointment-reminders.md <<MD
---
status: $1
date: 2026-10-20
decision-makers: lee
---

# SMS appointment reminders

## Summary

Epic: ABC-1

Text each patient an SMS reminder 24 hours before their appointment.

## Decision

$2
MD
}
design accepted "Approved by lee on 2026-10-20."
git add .gitignore .claude docs src
git commit -qm "Record the SMS appointment reminders design"
design proposed "Pending — lee."
git commit -qam "Reopen the SMS appointment reminders design"
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
