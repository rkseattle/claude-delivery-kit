#!/usr/bin/env bash
# A project.json complete except for one required key, parent_branch_default.
set -euo pipefail
mkdir -p .claude
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "source_roots": "src tests",
  "build_command": "make build",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection"
}
JSON
