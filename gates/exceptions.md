# Rule-book exceptions — the register format, and the kit's own

The rule book's "Tailoring and exceptions" section lets a "must" rule be waived only as a
recorded exception, reviewed while it stands and remediated or renewed once it expires.
This file defines the register that records them and holds the exceptions the kit itself
takes. A project's own register lives at `{{exceptions_log}}`; set to `none`, the project
has no register.

## Format

A register is one Markdown table with these columns, in this order:

| Column        | Holds                                                                  |
| ------------- | ---------------------------------------------------------------------- |
| `Rule`        | The rule or step waived, numbered where it is defined                  |
| `Reason`      | Why the run or the kit departs from it                                 |
| `Risk`        | What can go wrong while the exception stands                           |
| `Expiry`      | An ISO 8601 date, `YYYY-MM-DD`                                         |
| `Remediation` | The ticket that removes the exception, or what happens at expiry       |

A row has expired when its `Expiry` is before today's local date. An expired row is
remediated — the waived rule is followed again and the row comes out — or renewed with a
new `Expiry`, in a commit that says why it still holds. Removing or renaming a kit-wide
row updates, in the same commit, each `reference/rule-book-map.md` row that cites it. A
project register starts with the same header row.

## Kit-wide exceptions

These apply to every project using the kit.

| Rule | Reason | Risk | Expiry | Remediation |
| ---- | ------ | ---- | ------ | ----------- |
| Phase 2 step 2: ACs in Given/When/Then form | Each AC is already a testable clause ending `[verify: <tier> @ <evidence>]`, and `lint_draft.py` parses that format | A precondition a Given clause would state can go unwritten | 2027-04-08 | At expiry, renew, or file a CDK ticket to adopt Given/When/Then |
| Rule book Phase 3 step 8: design review by an engineer outside the immediate team, for a `plan-work` plan | A plan covers at most three tickets; `design-adversary` reviews it cold against its tickets and NFRs, and a feature's design takes the outside engineer's review under `gates/design-exit.md` | No plan gets an outside engineer's review, and no design does either until a skill applies `gates/design-exit.md` | 2027-04-20 | A skill applying `gates/design-exit.md` gives designs the review; at expiry, renew, or file a CDK ticket for an outside reviewer in `plan-work` |
| Phase 5 step 6: quarantine flaky tests | The kit root-causes every failure; a quarantine path lets a real failure be skipped as noise | A nondeterministic test blocks commits until it is root-caused | 2027-04-08 | At expiry, renew, or file a CDK ticket for a quarantine path |
| Rule book R1 and R11: project docs and decision records in version control | Plans and ticket drafts are working state; commits and the PR body carry the record | Rejected alternatives and design reasoning are gone after delivery | 2027-04-08 | At expiry, renew, or file a CDK ticket to commit decision records |
| Rule book R12: use the project's secret store | The kit holds no secrets and cannot name a project's store; its secret scans block a committed secret at every commit and push | A project keeps secrets outside any store, in an untracked file, unnoticed | 2027-04-18 | At expiry, renew, or file a CDK ticket to check for a named secret store |
| Rule book Appendix B1 Implementation: dependency and static-analysis scans in CI | The kit runs both scans at every commit and push, for every project, and blocks a new High; which jobs a project's CI runs is its mechanics gate | A push that bypasses the local gates reaches merge unscanned | 2027-04-18 | At expiry, renew, or file a CDK ticket to require the scans in CI |
| Rule book Section 10 exception rule 3: review open exceptions each iteration | `deliver` Step 0 lists every expired row at the start of each run; an unexpired row is reviewed at its expiry | An exception whose reason has lapsed stands until it expires | 2027-04-18 | At expiry, renew, or file a CDK ticket to review open rows each iteration |
| Rule book Section 10 exception rule 4: file an emergency exception within one working day | The kit has no production-emergency path to file one from; `release` rolls back first and reports | An emergency action taken outside the kit goes unrecorded | 2027-04-18 | At expiry, renew, or file a CDK ticket for an emergency-exception path |
