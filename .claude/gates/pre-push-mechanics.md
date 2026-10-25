# Pre-push mechanics — claude-delivery-kit

The commands behind `gates/pre-push.md` for this repo. One command runs all of them, in
CI's order, from the repo root:

```bash
bash scripts/ci/all.sh
```

Run it after `git add`: `json-parses.sh` reads tracked files only. `shellcheck.sh` pins
shellcheck 0.11.0 for both CI and local runs, downloading and checksumming it once when the
installed one differs.

## CI jobs and their local equivalents

| CI job · step | Local command |
| --- | --- |
| `hooks` · Stop-hook self-test | `bash hooks/block-false-stop.sh --self-test` |
| `hooks` · Branch-guard self-test | `bash hooks/protect-plan-branch.sh --self-test` |
| `hooks` · Hooks are wired | `bash scripts/ci/hooks-wired.sh` |
| `hooks` · Self-tests accept the hook path | `bash scripts/ci/hooks-relocatable.sh` |
| `script-tests` · Project rules self-test | `python3 gates/scripts/project_rules.py --self-test` |
| `script-tests` · Linter fixtures | `python3 skills/write-tickets/scripts/lint_draft.py --self-test` |
| `script-tests` · Review gate self-test | `python3 skills/ci-green/scripts/review_gate.py --self-test` |
| `script-tests` · README checker fixtures | `python3 skills/readme-docs/scripts/check_readme.py --self-test` |
| `script-tests` · SARIF gate self-test | `python3 gates/scripts/sarif_gate.py --self-test` |
| `script-tests` · Halt watch self-test | `python3 skills/release/scripts/halt_watch.py --self-test` |
| `script-tests` · Readiness check self-test | `python3 skills/release-readiness/scripts/readiness_check.py --self-test` |
| `script-tests` · Incident check self-test | `python3 skills/incident-review/scripts/incident_check.py --self-test` |
| `script-tests` · Maintenance check self-test | `python3 skills/maintenance-review/scripts/maintenance_check.py --self-test` |
| `script-tests` · Retirement check self-test | `python3 skills/retire-system/scripts/retire_check.py --self-test` |
| `script-tests` · Design check self-test | `python3 skills/design-feature/scripts/design_check.py --self-test` |
| `script-tests` · ADR number check self-test | `python3 gates/scripts/adr_numbers.py --self-test` |
| `script-tests` · ADR numbers are unique | `python3 gates/scripts/adr_numbers.py` |
| `manifest` · Every JSON file parses | `bash scripts/ci/json-parses.sh` |
| `manifest` · Frontmatter names | `bash scripts/ci/frontmatter-names.sh` |
| `manifest` · Line budget | `bash scripts/ci/line-budget.sh` |
| `manifest` · Bundled-file references | `bash scripts/ci/bundled-refs.sh` |
| `manifest` · Rule-book map paths resolve | `bash scripts/ci/rule-book-map.sh` |
| `manifest` · No declared key accepts its reference placeholder | `bash scripts/ci/config-examples.sh` |
| `manifest` · No project-specific tokens | `bash scripts/ci/no-leaks.sh` |
| `manifest` · Actions are pinned to commit SHAs | `bash scripts/ci/actions-pinned.sh` |
| `manifest` · Every CI step has a local equivalent | `bash scripts/ci/ci-steps-mirrored.sh` |
| `manifest` · CI scripts pass shellcheck | `bash scripts/ci/shellcheck.sh` |
| `manifest` · CI checks fail on their defects | `bash scripts/ci/self-test.sh` |
| `ci-passed` · Every job succeeded (the check to require) | `bash scripts/ci/all-jobs-passed.sh` |

A step added to `.github/workflows/ci.yml` gets a row here and a line in
`scripts/ci/all.sh` in the same commit; `ci-steps-mirrored.sh` fails CI otherwise.

## Post-failure procedure

No partial re-run allowance: after any failure, fix it and re-run `bash scripts/ci/all.sh`
in full. It takes under a minute, so there is no subset worth trusting instead.

## Failure shapes

- `OVER CAP <file>` — a line budget breach; the change names what comes out.
- `UNPARSEABLE cap table` — `skills/deliver/references/invariants.md` is missing, or its cap
  table lost a row, repeated one, or holds a cap that is not a whole number; fix the table.
- `BROKEN: <path>` — a malformed JSON file, or a `${CLAUDE_PLUGIN_ROOT}` reference git does
  not track exactly as written: a missing file, one not yet `git add`ed, or a wrong case.
  `cannot list the tracked files` from either reference check — run from a checkout git can
  read.
- `NOT PINNED` — a workflow's `uses:` names a tag, branch, or short SHA; pin it to the full
  commit SHA with the tag as a trailing comment. `UNPARSEABLE` — a workflow is not YAML
  with a `jobs:` mapping.
- `MISSING: <path>` — a `reference/rule-book-map.md` row names a path git does not track,
  exactly as written; point the row at the file that now applies the rule, `git add` a
  new one, or move prose holding a slash outside backticks. A path holding a space was
  wrapped across lines inside its backticks, or padded on one side only; rejoin or trim
  it. `no rule-book map at`, `no exceptions register at`, `names no path`, or `is not
  UTF-8` — the map or `gates/exceptions.md`, as named, is gone, emptied, or corrupted;
  restore it. `MISSING ROW:` — an Excepted by name starts no complete kit-wide row's
  `Rule` cell, up to its colon; point the map row at what now applies the rule, or at
  the renamed row. `NO EXCEPTED BY COLUMN:` — a map table lacks the column; add it. `NOT
  A REGISTER:` — a table under Kit-wide exceptions is not headed Rule | Reason | Risk |
  Expiry | Remediation; restore its header.
- `ACCEPTS:` or `UNDOCUMENTED:` from `config-examples.sh` — a `project_rules.PROJECT_KEYS`
  shape takes `reference/project-json.md`'s placeholder for its key as a real setting (give
  it `template_list`, or make its check reject the placeholder), or a registered key's dotted
  path is missing from the example blocks (add it there). `UNREGISTERED:` — a script declares
  a key at its top level that the registry lacks (register its shape); `UNREADABLE:` — a kit
  script cannot be read or parsed. `NO REFERENCE:` — the reference
  holds no json object block, one that cannot parse, or a key shown two ways; `NO SCHEMA:` or
  `NOTHING DECLARED:` — `gates/scripts/project_rules.py` is missing or its registry is empty.
- `FAIL <check>: <case>` from `self-test.sh` — a check stopped catching its defect; fix the
  check, never the case.
- A hook self-test count mismatch — the hook's behavior changed; read the named case.

## Pre-PR items

None beyond `gates/pre-push.md`.

## What CI does not cover

- **The eval suite.** `claude plugin eval . --scaffold` calls a judge model and costs
  money, so no CI job runs it. Run it when a stage skill, gate, or agent changes.
- **The `tac` branch of the Stop hook** runs only on Linux, so a Mac's local run never
  exercises it; CI is its only coverage.
- **Inspection-tier ACs.** Rob reads the changed text; no command stands in for that.
