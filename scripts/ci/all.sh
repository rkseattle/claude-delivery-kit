#!/usr/bin/env bash
# Every CI check, in CI's order, from the repo root: the local equivalent of a green CI run.
# Each line below is a `run:` command from .github/workflows/ci.yml, character for
# character; ci-steps-mirrored.sh fails if a CI step has no line here.
# Usage: scripts/ci/all.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
bash hooks/block-false-stop.sh --self-test
bash hooks/protect-plan-branch.sh --self-test
bash scripts/ci/hooks-wired.sh
bash scripts/ci/hooks-relocatable.sh
python3 skills/write-tickets/scripts/lint_draft.py --self-test
bash scripts/ci/json-parses.sh
bash scripts/ci/frontmatter-names.sh
bash scripts/ci/line-budget.sh
bash scripts/ci/bundled-refs.sh
bash scripts/ci/no-leaks.sh
bash scripts/ci/ci-steps-mirrored.sh
shellcheck scripts/ci/*.sh
bash scripts/ci/self-test.sh
