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
| `Rule`        | The rule or step waived, numbered as the rule book numbers it          |
| `Reason`      | Why the run or the kit departs from it                                 |
| `Risk`        | What can go wrong while the exception stands                           |
| `Expiry`      | An ISO 8601 date, `YYYY-MM-DD`                                         |
| `Remediation` | The ticket that removes the exception, or what happens at expiry       |

A row has expired when its `Expiry` is before today's local date. An expired row is
remediated — the waived rule is followed again and the row comes out — or renewed with a
new `Expiry`, in a commit that says why it still holds. A project register starts with the
same header row.

## Kit-wide exceptions

These apply to every project using the kit.

| Rule | Reason | Risk | Expiry | Remediation |
| ---- | ------ | ---- | ------ | ----------- |
| Phase 2 step 2: ACs in Given/When/Then form | Each AC is already a testable clause ending `[verify: <tier> @ <evidence>]`, and `lint_draft.py` parses that format | A precondition a Given clause would state can go unwritten | 2027-04-08 | At expiry, renew, or file a CDK ticket to adopt Given/When/Then |
| Phase 5 step 6: quarantine flaky tests | The kit root-causes every failure; a quarantine path lets a real failure be skipped as noise | A nondeterministic test blocks commits until it is root-caused | 2027-04-08 | At expiry, renew, or file a CDK ticket for a quarantine path |
| Rule book R1 and R11: project docs and decision records in version control | Plans and ticket drafts are working state; commits and the PR body carry the record | Rejected alternatives and design reasoning are gone after delivery | 2027-04-08 | At expiry, renew, or file a CDK ticket to commit decision records |
