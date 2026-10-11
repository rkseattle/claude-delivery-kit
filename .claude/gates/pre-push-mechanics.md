# Pre-push mechanics — claude-delivery-kit

The commands behind `gates/pre-push.md` for this repo. One command runs all of them, in
CI's order, from the repo root:

```bash
bash scripts/ci/all.sh
```

## CI jobs and their local equivalents

| CI job · step | Local command |
| --- | --- |
| `hooks` · Stop-hook self-test | `bash hooks/block-false-stop.sh --self-test` |
| `hooks` · Branch-guard self-test | `bash hooks/protect-plan-branch.sh --self-test` |
| `hooks` · Hooks are wired | `bash scripts/ci/hooks-wired.sh` |
| `hooks` · Self-tests accept the hook path | `bash scripts/ci/hooks-relocatable.sh` |
| `ticket-lint` · Linter fixtures | `python3 skills/write-tickets/scripts/lint_draft.py --self-test` |
| `manifest` · Every JSON file parses | `bash scripts/ci/json-parses.sh` |
| `manifest` · Frontmatter names | `bash scripts/ci/frontmatter-names.sh` |
| `manifest` · Line budget | `bash scripts/ci/line-budget.sh` |
| `manifest` · Bundled-file references | `bash scripts/ci/bundled-refs.sh` |
| `manifest` · No project-specific tokens | `bash scripts/ci/no-leaks.sh` |
| `manifest` · Every CI step has a local equivalent | `bash scripts/ci/ci-steps-mirrored.sh` |
| `manifest` · CI checks fail on their defects | `bash scripts/ci/self-test.sh` |

A step added to `.github/workflows/ci.yml` gets a row here and a line in
`scripts/ci/all.sh` in the same commit; `ci-steps-mirrored.sh` fails CI otherwise.

## Post-failure procedure

No partial re-run allowance: after any failure, fix it and re-run `bash scripts/ci/all.sh`
in full. It takes under a minute, so there is no subset worth trusting instead.

## Failure shapes

- `OVER CAP <file>` — a line budget breach; the change names what comes out.
- `BROKEN: <path>` — a malformed JSON file or a `${CLAUDE_PLUGIN_ROOT}` reference to a
  missing file.
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
