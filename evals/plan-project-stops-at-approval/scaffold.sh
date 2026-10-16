#!/usr/bin/env bash
# A git repo with one commit on main and a project.json whose build always passes, so the
# only stop left for plan-project is the sponsor's. origin is a local bare clone, so a
# fetch succeeds offline; the prompt stands in for GitHub's CI runs.
set -euo pipefail
git init -q
# The harness may have run git init already, which ignores -b; name the branch directly.
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src tests",
  "build_command": "true",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "brief_file": "docs/brief.md",
  "project_size": "small",
  "lifecycle_model": "iterative",
  "roles": { "sponsor": "dana" }
}
JSON
git add .claude/project.json
git commit -qm "Seed the project configuration"
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
