#!/usr/bin/env bash
# A project.json with every required key and no optional ones, so each optional key
# plan-work uses, design_dir and adr_dir among them, resolves to its documented default:
# none, [] for disciplines, 400 for pr_review_limit_lines, or the person running the
# session for each role in roles.
set -euo pipefail
mkdir -p .claude
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src tests",
  "build_command": "make build",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection"
}
JSON
