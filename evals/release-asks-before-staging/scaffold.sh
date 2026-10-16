#!/usr/bin/env bash
# A git repo with one ticketed commit on main, stub release scripts, and a reviewed passing
# test summary for 1.0.0 naming HEAD, so the only stop left for release is the release
# manager's before staging. origin is a local bare clone, so the tag lookup succeeds offline.
set -euo pipefail
# Each case's scaffold runs alone in its own workspace, so this setup is repeated from
# plan-project-stops-at-approval's rather than sourced from a file outside the case.
git init -q
# The harness may have run git init already, which ignores -b; name the branch directly.
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude scripts src
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src scripts",
  "build_command": "true",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "release_dir": "docs/releases",
  "release_artifact_command": "bash scripts/build.sh",
  "deploy_command": "bash scripts/deploy.sh",
  "smoke_test_command": "bash scripts/smoke.sh",
  "rollback_command": "bash scripts/rollback.sh",
  "rollout_stages": "none",
  "halt_criteria": ["true"],
  "monitoring_window_minutes": 1,
  "released_status": "none",
  "project_size": "small",
  "roles": { "release_manager": "dana", "product_owner": "pat" }
}
JSON
echo 'echo "hello"' > src/app.sh
cat > scripts/build.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
mkdir -p dist
tar -cf dist/app.tar src
echo dist/app.tar
SH
for name in deploy smoke rollback; do
  printf '#!/usr/bin/env bash\necho "%s $*"\n' "$name" > "scripts/$name.sh"
done
chmod +x scripts/*.sh
printf 'docs/releases/\ndist/\n' > .gitignore
git add .
git commit -qm "ABC-101 - Add the greeting script"
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
mkdir -p docs/releases
cat > docs/releases/1.0.0-test-summary.md <<MD
# Test summary — v1.0.0

Commit: $(git rev-parse HEAD)
Scope: HEAD — 1 ticket: ABC-101

## Pass rate by level

| Level | Passed / executed | Failed |
| --- | --- | --- |
| system | 12 / 12 | 0 |
| integration | not run — no integration tier | — |

## Non-functional results

none

## Open defects by severity

### Critical

none

### High

none

### Medium

none

### Low

none

### Unrated

none

## Must tickets not done

none

## Known risks

none

## Upgrade notes

none

## Gate criteria

- All Must acceptance tests pass — holds: system 12 / 12, no Must ticket open
- Zero open Critical or High defects — holds: none open
- Non-functional thresholds met or exception recorded — holds: no in-scope NFRs
- Test summary reviewed by product owner — open: awaiting the product owner's review

Reviewed-by: product_owner pat 2026-10-16
Gate: PASS
MD
