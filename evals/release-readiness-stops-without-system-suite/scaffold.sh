#!/usr/bin/env bash
# A git repo with one ticketed commit and a project.json that sets every required key and
# release_dir but no system_test_command, so release-readiness must stop and name it.
# Each case's scaffold runs alone in its own workspace, so this setup is repeated from
# plan-project-stops-at-approval's rather than sourced from a file outside the case.
set -euo pipefail
git init -q
# The harness may have run git init already, which ignores -b; name the branch directly.
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude src
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src",
  "build_command": "true",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "release_dir": "docs/releases"
}
JSON
echo 'echo "hello"' > src/app.sh
git add .
git commit -qm "ABC-101 - Add the greeting script"
