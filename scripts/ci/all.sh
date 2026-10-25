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
python3 gates/scripts/project_rules.py --self-test
python3 skills/write-tickets/scripts/lint_draft.py --self-test
python3 skills/ci-green/scripts/review_gate.py --self-test
python3 skills/readme-docs/scripts/check_readme.py --self-test
python3 gates/scripts/sarif_gate.py --self-test
python3 skills/release/scripts/halt_watch.py --self-test
python3 skills/release-readiness/scripts/readiness_check.py --self-test
python3 skills/incident-review/scripts/incident_check.py --self-test
python3 skills/maintenance-review/scripts/maintenance_check.py --self-test
python3 skills/retire-system/scripts/retire_check.py --self-test
python3 skills/design-feature/scripts/design_check.py --self-test
python3 gates/scripts/adr_numbers.py --self-test
python3 gates/scripts/adr_numbers.py
bash scripts/ci/json-parses.sh
bash scripts/ci/frontmatter-names.sh
bash scripts/ci/line-budget.sh
bash scripts/ci/bundled-refs.sh
bash scripts/ci/rule-book-map.sh
bash scripts/ci/config-examples.sh
bash scripts/ci/no-leaks.sh
bash scripts/ci/actions-pinned.sh
bash scripts/ci/ci-steps-mirrored.sh
bash scripts/ci/shellcheck.sh
bash scripts/ci/self-test.sh
bash scripts/ci/all-jobs-passed.sh
