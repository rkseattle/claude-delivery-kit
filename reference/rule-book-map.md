# Rule-book map — the kit file that applies each rule

One row per standing rule, phase exit criterion, Phase 7 ongoing check, Section 10
exception rule, and Appendix B addendum item in
`reference/software-engineering-rule-book.md`. Each row names the kit files that apply the
item and the step or section in each that does it. Where no kit file applies an item, or
applies only part of it, its Excepted by cell names each `gates/exceptions.md` kit-wide
row that records the departure, by its Rule text up to the colon, in plain text, separated
by semicolons.

Every backticked token containing a slash is a path from the repo root, and CI's
`Rule-book map paths resolve` step fails when one is not a tracked file, or when an
Excepted by name starts no complete kit-wide row. Write a step name or any other text
holding a slash outside backticks, and cite an exception only in Excepted by. The step
catches a moved or deleted file, not a renamed heading: a change that renames a step cited
here updates its row in the same commit.

## Standing rules

| ID | Rule | Applied by | Step or section | Excepted by |
| --- | --- | --- | --- | --- |
| R1 | Everything in version control; every change traceable to a ticket | `skills/implement-phases/SKILL.md`; `gates/pre-push.md`; `skills/ship-pr/SKILL.md`; `gates/exceptions.md` | 2d. Definition of Done, then commit; PR conventions, and step 11, a clean-checkout build; Step 4 — Push and open the PR. Plans and decision records stay out of version control, excepted | Rule book R1 and R11 |
| R2 | Review by someone other than the author before main | `skills/ship-pr/SKILL.md`; `skills/ci-green/SKILL.md`; `skills/ci-green/scripts/review_gate.py` | Step 4 — Push and open the PR (the reviewer set); Step 5 — Loop (the approval, or the per-project R2 exception); the reviewer-set and approval subcommands | |
| R3 | One stated responsibility and a documented interface per module | `skills/plan-work/SKILL.md`; `gates/rule-book-review.md`; `gates/definition-of-done.md` | Components and interfaces; Module boundaries — R3, R4, checks 6 and 7; Cross-cutting obligations, the public-interface row | |
| R4 | No reaching into another module's internals or data store | `gates/rule-book-review.md`; `skills/plan-work/SKILL.md`; `agents/greptile-reviewer.md` | Module boundaries — R3, R4, check 6; Data ownership; Review dimensions, item 5 | |
| R5 | One authoritative definition; extract on the third occurrence | `gates/rule-book-review.md`; `gates/definition-of-done.md`; `agents/commit-adversary.md` | Duplication — R5, checks 1–3; Before git add; Substance | |
| R6 | Build only what an accepted requirement needs | `skills/deliver/references/invariants.md`; `agents/commit-adversary.md`; `skills/write-tickets/references/templates.md` | Fixing is the default; deferring needs permission; Scope; Sections by type, the Out of scope section | |
| R7 | Tests that would fail if the change were reverted | `agents/commit-adversary.md`; `agents/greptile-reviewer.md`; `gates/definition-of-done.md`; `gates/status-report.md` | Substance; Review dimensions, item 7 Tests; Conditional gates, a defect fix; 4. Acceptance criteria, evidence that fails if the behavior regresses | |
| R8 | Errors handled or surfaced; input validated at trust boundaries | `gates/rule-book-review.md`; `gates/definition-of-done.md`; `agents/greptile-reviewer.md` | Errors and input — R8, checks 4 and 5; Domain subsystems, failure modes of a new outbound call; Review dimensions, items 1 and 3 | |
| R9 | Small increments; a PR reviewable in under an hour | `gates/pre-push.md`; `skills/plan-work/SKILL.md`; `skills/ship-pr/SKILL.md` | Pre-push checklist, step 2, diff size; Size: at most 6 phases; Step 4 — Push and open the PR | |
| R10 | One-command build from a clean checkout; pinned dependencies | `gates/pre-push.md`; `gates/planning-exit.md`; `gates/definition-of-done.md`; `scripts/ci/actions-pinned.sh` | Pre-push checklist, step 11, a clean-checkout build; What settles each one, criterion 4; Cross-cutting obligations, the dependency row; and, for this repo's own CI only, actions pinned to SHAs | |
| R11 | Decision records for costly-to-reverse choices | `skills/write-tickets/references/templates.md`; `skills/write-tickets/SKILL.md`; `gates/exceptions.md` | Sections by type, a spike Task's decision record; Step 1 — Settle the decisions. A plan's own choices are excepted | Rule book R1 and R11 |
| R12 | Secrets never committed; use the project's secret store | `gates/definition-of-done.md`; `gates/pre-push.md`; `gates/exceptions.md` | The gate, step 7, secret scan; Pre-push checklist, step 8, secret scan. The secret store is excepted | Rule book R12 |

## Phase exit criteria

| ID | Criterion | Applied by | Step or section | Excepted by |
| --- | --- | --- | --- | --- |
| P1.1 | Brief approved by sponsor | `gates/planning-exit.md`; `skills/plan-project/SKILL.md` | What settles each one, criterion 1; Step 4 — Stop for the sponsor, and Step 5 — Record the decision and commit | |
| P1.2 | Non-goals stated | `gates/planning-exit.md`; `skills/plan-project/SKILL.md` | What settles each one, criterion 2; Step 2 — Write the brief | |
| P1.3 | Risk list with owners exists | `gates/planning-exit.md`; `skills/plan-project/SKILL.md` | What settles each one, criterion 3; Step 2 — Write the brief | |
| P1.4 | Repository and CI run a passing empty build | `gates/planning-exit.md`; `skills/plan-project/SKILL.md` | What settles each one, criterion 4; Step 3 — Confirm the repository and CI | |
| P2.1 | Must requirements' ACs reviewed by QA | `skills/write-tickets/SKILL.md`; `skills/write-tickets/references/rubric.md`; `gates/exceptions.md` | Step 7 — Present for approval (QA confirms every Must ticket's ACs); rubric R12 Prioritized. Only the AC form is excepted; the QA review applies | Phase 2 step 2 |
| P2.2 | NFRs have numeric thresholds | `skills/write-tickets/references/rubric.md`; `skills/write-tickets/scripts/lint_draft.py`; `agents/ticket-adversary.md` | rubric R13 Measurable non-functional requirements; the linter's R13 finding; What to attack, per ticket | |
| P2.3 | Every requirement links to a goal | `skills/write-tickets/references/rubric.md`; `skills/write-tickets/SKILL.md`; `skills/write-tickets/scripts/lint_draft.py` | rubric R14 Traceable to a goal; Step 4 — Draft; the linter's R14 finding | |
| P2.4 | Product owner signs off on the baseline | `skills/write-tickets/SKILL.md`; `skills/write-tickets/references/rubric.md` | Step 7 — Present for approval; rubric R15 Change impact recorded | |
| P3.1 | Component diagram and interfaces reviewed | `skills/plan-work/SKILL.md`; `agents/design-adversary.md` | Components and interfaces, and Step 6 — Present for approval (the tech lead); Completeness | |
| P3.2 | Decision records exist for irreversible choices | `skills/plan-work/SKILL.md`; `gates/exceptions.md` | Rejected alternatives. Committed records are excepted | Rule book R1 and R11 |
| P3.3 | Test strategy approved by QA | `skills/plan-work/SKILL.md`; `agents/design-adversary.md` | Test strategy, and Step 6 — Present for approval (QA); Completeness | |
| P3.4 | Each NFR has a design element | `skills/plan-work/SKILL.md`; `agents/design-adversary.md` | NFR coverage; Output, BLOCKER | |
| P4.1 | CI green: build, lint, unit and integration tests | `skills/ci-green/SKILL.md`; `gates/pre-push.md` | Step 5 — Loop; Pre-push checklist, steps 3, 5, 6 and 11 | |
| P4.2 | At least one approving review | `skills/ci-green/SKILL.md`; `skills/ci-green/scripts/review_gate.py` | Step 5 — Loop, the approval; the approval subcommand | |
| P4.3 | Acceptance criteria demonstrably met | `skills/branch-review/SKILL.md`; `agents/greptile-reviewer.md`; `skills/implement-phases/SKILL.md` | Step 5 — Verify the acceptance criteria table; Acceptance criteria check; 2d. Definition of Done, then commit | |
| P4.4 | Docs and interface definitions updated | `gates/definition-of-done.md`; `gates/rule-book-review.md`; `agents/commit-adversary.md` | Cross-cutting obligations, the public-interface and Behavior a user can see rows; Module boundaries — R3, R4, check 7; Substance | |
| P5.1 | All Must acceptance tests pass | `gates/release-readiness.md`; `skills/release-readiness/SKILL.md`; `skills/release-readiness/scripts/readiness_check.py` | What settles each one, criterion 1; Step 3 — Run the suites, and Step 4 — Jira and the merged PRs; the criteria subcommand | |
| P5.2 | Zero open Critical or High defects | `gates/release-readiness.md`; `skills/release-readiness/SKILL.md` | What settles each one, criterion 2; Step 4 — Jira and the merged PRs | |
| P5.3 | Non-functional thresholds met or exception recorded | `gates/release-readiness.md`; `skills/release-readiness/scripts/readiness_check.py` | What settles each one, criterion 3; the settle subcommand | |
| P5.4 | Test summary reviewed by product owner | `gates/release-readiness.md`; `skills/release-readiness/SKILL.md` | What settles each one, criterion 4; Step 6 — Stop for the product owner, and Step 7 — Record the review | |
| P6.1 | Rollback tested in staging | `gates/release.md`; `skills/release/SKILL.md` | What settles each one, criterion 1; Step 5 — Staging, then each production stage | |
| P6.2 | Smoke tests pass in production | `gates/release.md`; `skills/release/SKILL.md` | What settles each one, criterion 2; Step 5 — Staging, then each production stage | |
| P6.3 | No halt criterion triggered during the monitoring window | `gates/release.md`; `skills/release/SKILL.md`; `skills/release/scripts/halt_watch.py` | What settles each one, criterion 3; Step 5 — Staging, then each production stage; the watch it runs per stage | |
| P6.4 | Release notes published | `gates/release.md`; `skills/release/SKILL.md` | What settles each one, criterion 4; Step 4 — Write the release notes, and Step 6 — Publish and update the tickets | |

## Phase 7 ongoing checks

| ID | Check | Applied by | Step or section | Excepted by |
| --- | --- | --- | --- | --- |
| P7.1 | Owner and on-call rota named | `skills/maintenance-review/SKILL.md` | Step 3 — Report, Ownership | |
| P7.2 | Alerts route to a person, not just a channel | `skills/maintenance-review/SKILL.md`; `skills/maintenance-review/scripts/maintenance_check.py` | Step 2 — Gather, alert routes; Step 3 — Report, Alert routes | |
| P7.3 | Incident reviews have closed follow-ups | `skills/maintenance-review/SKILL.md`; `skills/incident-review/SKILL.md` | Step 2 — Gather, old incident follow-ups; Step 5 — Create the approved tickets, then commit | |
| P7.4 | No dependency with a known Critical vulnerability past its patch SLA | `skills/maintenance-review/SKILL.md`; `skills/maintenance-review/scripts/maintenance_check.py` | Step 2 — Gather, vulnerabilities past the SLA; Step 3 — Report, Vulnerabilities past the patch SLA | |

## Section 10 exception rules

| ID | Rule | Applied by | Step or section | Excepted by |
| --- | --- | --- | --- | --- |
| X1 | A "must" rule is waived only by the tech lead, or the sponsor for Phase 1 and 2 rules | `skills/deliver/SKILL.md`; `skills/ci-green/SKILL.md` | Invariants across every stage, a skipped "must" step is a recorded exception; Step 5 — Loop | |
| X2 | Record each exception: rule, reason, risk, expiry, remediation | `gates/exceptions.md`; `skills/deliver/SKILL.md`; `skills/release-readiness/scripts/readiness_check.py` | Format; Invariants across every stage; the exceptions reader | |
| X3 | Review open exceptions each iteration; remediate or renew expired ones | `skills/deliver/SKILL.md`; `gates/exceptions.md` | Step 0 — Resume or start fresh, expired rows; Format. Review of unexpired rows is excepted | Rule book Section 10 exception rule 3 |
| X4 | In a production emergency, act first and file the exception within one working day | `gates/exceptions.md` | Kit-wide exceptions, the row in Excepted by; no other kit file applies it | Rule book Section 10 exception rule 4 |

## Appendix B addenda

| ID | Item | Applied by | Step or section | Excepted by |
| --- | --- | --- | --- | --- |
| B1.D | Security, Design: threat model; High threats mitigated | `skills/plan-work/SKILL.md`; `agents/design-adversary.md` | Threat model; Completeness, and Output, BLOCKER | |
| B1.I | Security, Implementation: scans in CI; a new High blocks merge | `gates/definition-of-done.md`; `gates/pre-push.md`; `gates/scripts/sarif_gate.py`; `gates/exceptions.md` | The gate, steps 6 and 8; Pre-push checklist, steps 7 and 9; the new-findings subcommand both call. Running them in CI is excepted | Rule book Appendix B1 Implementation |
| B1.R | Security, Deployment: sign-off for auth, authz or data-handling changes | `gates/release.md`; `skills/release/SKILL.md` | Discipline addenda, security; Step 2 — The scope | |
| B1.M | Security, Maintenance: Critical vulnerabilities patched within SLA | `skills/maintenance-review/SKILL.md`; `gates/exceptions.md` | Step 3 — Report, Critical vulnerabilities past the patch SLA; Format, for exceptions | |
| B2.Q | Data and ML, Requirements: sources, retention, privacy; model thresholds | `skills/write-tickets/references/templates.md`; `skills/write-tickets/references/rubric.md`; `skills/write-tickets/scripts/lint_draft.py` | Sections by type; D1–D4 Discipline fields; the D1 and D2 findings | |
| B2.D | Data and ML, Design: versioned datasets; a schema owner per dataset | `skills/plan-work/SKILL.md`; `agents/design-adversary.md` | Data ownership; Completeness | |
| B2.T | Data and ML, Testing: data-quality checks; no model regression | `gates/release-readiness.md`; `skills/release-readiness/SKILL.md` | Discipline addenda, data-ml; Step 5 — Write the summary, Discipline checks | |
| B2.M | Data and ML, Maintenance: drift threshold triggers retraining or rollback | `skills/maintenance-review/SKILL.md` | Step 2 — Gather, drift; Step 4 — Propose the tickets | |
| B3.R | Mobile, Deployment: phased store release; remote feature flags | `gates/release.md`; `skills/release/scripts/halt_watch.py` | Discipline addenda, mobile; the mobile rollout-stage rule | |
| B3.B | Mobile, Rollback: backward-compatible API; a minimum supported version | `gates/release.md` | Discipline addenda, mobile, the API-compatibility check | |
| B3.T | Mobile, Testing: device and OS-version matrix | `gates/release-readiness.md` | Discipline addenda, mobile | |
| B4.D | Embedded, Design: memory, power and timing as NFRs | `skills/write-tickets/references/templates.md`; `skills/write-tickets/scripts/lint_draft.py` | Sections by type; the D3 finding | |
| B4.T | Embedded, Testing: hardware-in-the-loop tests | `gates/release-readiness.md` | Discipline addenda, embedded | |
| B4.R | Embedded, Deployment: atomic update with a fallback image | `gates/release.md` | Discipline addenda, embedded | |
| B5.Q | SRE, Requirements: SLOs with a measurement window | `skills/write-tickets/references/templates.md`; `skills/write-tickets/scripts/lint_draft.py` | Sections by type; the D4 finding | |
| B5.R | SRE, Deployment: remaining error budget gates the release | `gates/release.md`; `skills/release/SKILL.md` | Discipline addenda, sre; Step 2 — The scope | |
| B5.M | SRE, Maintenance: each alert maps to an SLO and links a runbook | `skills/maintenance-review/SKILL.md` | Step 2 — Gather, alert rules; Step 3 — Report, Alert rules | |
