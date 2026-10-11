# Software Engineering Rule Book

Oct 8, 2026 · @Rob Kruy

## Purpose and use

This rule book sets the minimum policies and procedures for a general software project. Section 2 lists standing rules that apply in every phase. Sections 3–9 cover each phase with a policy (what must be true), a procedure (the steps), and exit criteria (the gate to the next phase).

- **"Must"** marks a required rule. Skipping it needs a recorded exception (Section 10).
- **"Should"** marks a default. Deviating needs a reason in the project log, not approval.
- Each phase names an owner. On a small team one person may hold several roles.
- The phases describe kinds of work. In iterative projects they repeat each cycle; the exit criteria still apply per cycle.

## Standing rules (all phases)

Each rule maps to a core principle. These apply to every artifact: requirements, designs, code, tests, and configuration.

| # | Rule | Principle |
| --- | --- | --- |
| R1 | All code, configuration, infrastructure definitions, and project docs must live in version control. Every change must be traceable to a ticket. | Version control, reproducibility |
| R2 | No change reaches the main branch without review by at least one person other than the author. | Readability, maintainability |
| R3 | Each module must have one stated responsibility and a documented interface. Callers depend only on the interface. | Cohesion, abstraction, information hiding |
| R4 | Modules should not reach into another module's internal state or data store. Cross-module calls go through public interfaces. | Low coupling, separation of concerns |
| R5 | Each fact (a business rule, constant, schema) has one authoritative definition. Extract shared logic on its third occurrence, not earlier. | DRY, rule of three |
| R6 | Build only what a current, accepted requirement needs. Record speculative ideas in the backlog, not the code. | YAGNI, simplicity |
| R7 | Every change must ship with automated tests that would fail if the change were reverted. | Testability, continuous verification |
| R8 | Errors must be handled explicitly or surfaced. Swallowing an exception without logging is prohibited. Validate input at trust boundaries. | Fail explicitly |
| R9 | Work is delivered in small increments. A pull request should be reviewable in under one hour. | Incremental delivery |
| R10 | Builds must be reproducible from a clean checkout with one documented command. Dependency versions must be pinned. | Reproducibility |
| R11 | Decisions that are costly to reverse are recorded in a decision record: context, options, choice, consequences. | Managing complexity |
| R12 | Secrets must never be committed. Use the project's secret store. | Fail explicitly, security |

## Phase 1: Planning

**Owner:** project lead. **Policy:** No implementation work starts until scope, success measures, and top risks are written and approved by the sponsor.

**Procedure**

1. Write a one-page project brief: problem, target users, goals, non-goals, and success measures with numeric targets.
2. List constraints: deadline, budget, team size, required platforms, compliance obligations.
3. Identify the top five risks. For each, record likelihood (low/medium/high), impact, and a mitigation or fallback.
4. Choose a lifecycle model (Section 10) and iteration length.
5. Produce a rough estimate as a range (for example, 6–10 weeks), not a single date.
6. Set up the repository, ticket tracker, CI pipeline, and communication channel (R1, R10).
7. Review the brief with the sponsor and record the decision.

**Exit criteria**

- [ ] Brief approved by sponsor
- [ ] Non-goals stated
- [ ] Risk list with owners exists
- [ ] Repository and CI pipeline run a passing empty build

## Phase 2: Requirements

**Owner:** product owner. **Policy:** Every requirement must be testable, prioritized, and traceable to a goal in the brief. A requirement no one can write a test for is not accepted.

**Procedure**

1. Gather needs from users and stakeholders through interviews, existing tickets, and support data.
2. Write each functional requirement as a ticket with a unique ID and acceptance criteria in Given/When/Then form.
3. Write non-functional requirements with measurable thresholds: for example, "p95 response under 300 ms at 200 requests/second," not "fast."
4. Prioritize with MoSCoW (Must, Should, Could, Won't). Mark Won't items explicitly (R6).
5. Have QA or a test engineer review each requirement for testability before acceptance.
6. Link each requirement to the brief goal it serves. Remove any that serve none.
7. Baseline the set. After baseline, changes go through the backlog with an impact note.

**Exit criteria**

- [ ] All Must requirements have acceptance criteria reviewed by QA
- [ ] Non-functional requirements have numeric thresholds
- [ ] Every requirement links to a goal
- [ ] Product owner signs off on the baseline

## Phase 3: Design

**Owner:** tech lead. **Policy:** The architecture must be documented and reviewed before implementation of the affected components begins. Module boundaries are drawn around decisions likely to change (R3, R4).

**Procedure**

1. Draw a component diagram showing each module, its single responsibility, and its dependencies.
2. For each module boundary, define the interface: inputs, outputs, errors, and versioning approach.
3. List the design decisions most likely to change (vendor, storage engine, external API) and confirm each is hidden behind one interface.
4. Separate concerns into layers: presentation, domain logic, data access, integration.
5. Define the data model and the single owner of each data store (R5).
6. Write a decision record for each choice that is costly to reverse (R11). Include at least two options considered.
7. Write a test strategy: which levels (unit, integration, system, acceptance) cover which risks, and the coverage target.
8. Run a design review with at least one engineer outside the immediate team. Check against requirements and non-functional thresholds.

**Exit criteria**

- [ ] Component diagram and interfaces reviewed
- [ ] Decision records exist for irreversible choices
- [ ] Test strategy approved by QA
- [ ] Each non-functional requirement has a design element that addresses it

## Phase 4: Implementation

**Owner:** each engineer for their change; tech lead for standards. **Policy:** Code merges to main only through a pull request that passes CI and review (R2, R7). Main must stay releasable at all times.

**Procedure**

1. Pick a ticket with accepted acceptance criteria. Create a short-lived branch named for the ticket ID.
2. Write or update tests alongside the code. Tests must fail without the change (R7).
3. Follow the project style guide; enforce it with an automated linter and formatter in CI.
4. Keep functions short and names descriptive. Comment why, not what.
5. Handle errors explicitly; log with context; validate external input (R8). Never commit secrets (R12).
6. Keep the pull request small (R9). Split large features behind a feature flag.
7. Open the pull request with a description: ticket link, what changed, how it was tested, risks.
8. The reviewer checks: correctness against acceptance criteria, tests, interface boundaries (R3, R4), duplication (R5), unneeded scope (R6), and readability.
9. Resolve all review comments, rebase on main, confirm CI passes, merge, and delete the branch.

**Exit criteria (per change)**

- [ ] CI green: build, lint, unit and integration tests
- [ ] At least one approving review
- [ ] Acceptance criteria demonstrably met
- [ ] Docs and interface definitions updated if behavior changed

## Phase 5: Testing

**Owner:** QA lead. **Policy:** A release candidate ships only when every Must requirement passes its acceptance tests and no open defect is rated Critical or High. Verification (built to spec) and validation (meets user need) are both required.

**Procedure**

1. Maintain the test levels from the test strategy:
   - Unit: per module, run on every commit.
   - Integration: across module interfaces and external services, run on every pull request.
   - System: end-to-end flows in a production-like environment, run on every release candidate.
   - Acceptance: against requirement acceptance criteria, with the product owner.
2. Run non-functional tests against the thresholds set in Phase 2: load, security scan, accessibility, as applicable.
3. Log each defect with steps to reproduce, expected and actual result, severity, and environment.
4. Rate severity: Critical (data loss, security breach, outage), High (core function broken, no workaround), Medium (workaround exists), Low (cosmetic).
5. For every fixed defect, add a regression test before closing it.
6. Track flaky tests separately; fix or quarantine within one iteration. A quarantined test needs an owner and ticket.
7. Produce a test summary: pass rate per level, open defects by severity, untested requirements, known risks.

**Exit criteria**

- [ ] All Must acceptance tests pass
- [ ] Zero open Critical or High defects
- [ ] Non-functional thresholds met or exception recorded
- [ ] Test summary reviewed by product owner

## Phase 6: Deployment

**Owner:** release manager (often the tech lead). **Policy:** Deployments must be automated, repeatable, and reversible. Every release must have a tested rollback path before it starts.

**Procedure**

1. Build the release artifact once from a tagged commit. Promote the same artifact through every environment (R10).
2. Store environment configuration separately from code; manage secrets in the secret store (R12).
3. Write release notes: changes, migrations, known issues, rollback steps.
4. Make database migrations backward compatible so the previous version can run against the new schema.
5. Deploy to staging and run smoke tests.
6. Roll out to production in stages (canary or percentage rollout) where the platform allows. Define the halt criteria beforehand: for example, error rate above 1% or p95 latency 20% above baseline.
7. Monitor dashboards and alerts for a set window (for example, one hour) after each stage.
8. On a halt criterion, roll back first and investigate second.
9. Announce completion and update the ticket and release log.

**Exit criteria**

- [ ] Rollback tested in staging
- [ ] Smoke tests pass in production
- [ ] No halt criterion triggered during the monitoring window
- [ ] Release notes published

## Phase 7: Maintenance

**Owner:** service owner (named team). **Policy:** Every production system has a named owner, monitoring, and an incident process. Changes in maintenance follow the same rules as new work (Phases 2–6, scaled down).

**Procedure**

1. Monitor availability, error rate, latency, and resource use against defined thresholds; alert the on-call owner.
2. Classify incoming work: corrective (defects), adaptive (environment or dependency changes), perfective (enhancements), preventive (refactoring, debt).
3. For incidents, restore service first, then hold a blameless review within five working days. Record cause, impact, and follow-up tickets.
4. Update dependencies on a fixed schedule (for example, monthly) and apply security patches within the SLA set by the organization.
5. Reserve a fixed share of each iteration for technical debt and preventive work. 10–20% is a common starting point; adjust based on defect trends.
6. Keep runbooks and architecture docs current. Review them at least once a quarter.
7. When retiring a system, notify users, migrate or archive data, and remove infrastructure and credentials.

**Ongoing checks**

- [ ] Owner and on-call rota named
- [ ] Alerts route to a person, not just a channel
- [ ] Incident reviews have closed follow-ups
- [ ] No dependency with a known Critical vulnerability past its patch SLA

## Tailoring and exceptions

Scale the documentation to the project; keep the gates. The standing rules (R1–R12) apply at every size.

| Project size | Planning and requirements | Design | Process |
| --- | --- | --- | --- |
| Small (1–2 people, under 1 month) | Brief and requirements can be one page | Short diagram plus decision records; peer review can be informal | Reviews by one peer; staged rollout optional |
| Medium (3–10 people) | Full procedure as written | Formal design review | As written |
| Large or regulated (10+ people, or compliance obligations) | Add traceability matrix and formal change control | Add security and privacy review | Add independent QA sign-off and audit trail |

**Lifecycle model**

- **Waterfall:** each phase runs once; exit criteria are formal gates. Use when requirements are fixed and change is costly (hardware integration, contracts).
- **Iterative / Agile:** Phases 2–6 run each iteration on a slice of scope; Phase 1 runs once with periodic review; exit criteria apply per iteration and per story.
- **Continuous delivery:** Phases 4–6 run per change through the pipeline; the gates are encoded as automated checks.

**Exceptions**

1. Any "must" rule may be waived only by the tech lead (or sponsor, for Phase 1 and 2 rules).
2. Record each exception in the project log: rule, reason, risk, expiry date, and remediation ticket.
3. Review open exceptions at each iteration or milestone review. Expired exceptions must be remediated or renewed.
4. In a production emergency, act first and file the exception within one working day.

## Appendix A: Responsibility matrix

Each phase has exactly one Accountable discipline, matching the phase owners in Sections 3–9. Drop rows for disciplines the project lacks and assign their R entries to whoever covers that work.

**R** = Responsible (does the work) · **A** = Accountable (owns the outcome, signs off the gate) · **C** = Consulted · **I** = Informed

| Discipline | Planning | Requirements | Design | Implementation | Testing | Deployment | Maintenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Project lead / product management | A | A | C | I | C | I | C |
| Tech lead / architecture | R | C | A | A | C | C | C |
| Application engineering (frontend, backend, mobile, full-stack, embedded) | C | C | R | R | R | R | A |
| QA / SDET | C | R | R | C | A | C | C |
| DevOps / build and release | R | I | C | C | C | A | R |
| Platform / infrastructure | C | I | C | C | I | R | R |
| SRE | I | C | C | I | R | R | R |
| Security | C | C | R | C | R | C | R |
| Data engineering / database | I | C | R | R | R | R | R |
| ML / AI engineering | C | C | R | R | R | R | R |
| UX design | C | R | R | C | C | I | C |
| Technical writing | I | C | I | C | I | R | C |

What the main R entries cover:

- QA in Requirements: testability review of acceptance criteria. In Design: the test strategy.
- Security in Design: threat model. In Testing: security scans. In Maintenance: patching within SLA.
- SRE in Requirements (C): proposes SLOs. In Testing: load tests. In Deployment: rollout monitoring and halt calls.
- Application engineering in Maintenance: the service owner role from Phase 7.
- Technical writing in Deployment: release notes and user-facing docs.

## Appendix B: Discipline addenda

These add to or replace specific steps in Sections 3–9. Apply an addendum only when the project includes that discipline's work. Disciplines not listed follow the main procedure unchanged.

### B1. Security

- **Design:** must produce a threat model (for example, STRIDE) for each component that handles external input, credentials, or personal data. Add an exit criterion: threats rated High have a mitigation in the design.
- **Implementation:** dependency and static-analysis scans run in CI; a new High finding blocks merge.
- **Deployment:** security sign-off is required for releases that change authentication, authorization, or data handling.
- **Maintenance:** Critical vulnerabilities are patched within the organization's SLA; track exceptions under Section 10.

### B2. Data and ML

- **Requirements:** state data sources, retention, and privacy constraints. For models, set numeric evaluation thresholds (for example, precision and recall on a named holdout set) as acceptance criteria.
- **Design:** version datasets, features, and models alongside code (R1). Define the schema owner for each dataset (R5).
- **Testing:** add data-quality checks (nulls, ranges, row counts) and model evaluation against a fixed benchmark set. A model release must not regress past its threshold.
- **Maintenance:** monitor input drift and output quality. Define a drift threshold that triggers retraining or rollback.

### B3. Mobile

- **Deployment:** app-store review replaces immediate rollout. Use the stores' phased release where available, and gate new behavior behind remote feature flags so it can be disabled without a new build.
- **Rollback:** a shipped binary cannot be recalled. Keep the server API backward compatible with every supported app version, and set a minimum supported version.
- **Testing:** test on a defined device and OS-version matrix, including the oldest supported OS.

### B4. Embedded and firmware

- **Design:** document hardware constraints (memory, power, timing) as non-functional requirements.
- **Testing:** add hardware-in-the-loop tests on target hardware; simulator results alone do not meet the Testing exit criteria.
- **Deployment:** firmware updates must be atomic with a fallback image (A/B partitions or equivalent). A failed update must not brick the device.

### B5. SRE

- **Requirements:** express availability and latency as SLOs with a measurement window (for example, 99.9% of requests under 300 ms over 30 days).
- **Deployment:** the remaining error budget is a release gate. When the budget is spent, only reliability fixes ship until it recovers.
- **Maintenance:** each alert must map to an SLO or a documented failure mode and link to a runbook.

## Appendix C: Role reference

One row per role: what it owns, the widely used practices and standards it follows, and what it produces. Named standards are the common industry references; a project adopts the ones that apply. The standing rules (R1–R12) apply to every role and are not repeated here.

### C1. Product, design, and application roles

| Role | Responsibilities | Best practices | Outputs |
| --- | --- | --- | --- |
| Project lead / product management | Scope, priorities, stakeholder alignment, release decisions | Measurable success metrics; explicit non-goals; MoSCoW or RICE prioritization; outcome-based roadmaps; regular backlog grooming | Project brief, prioritized backlog, roadmap, acceptance sign-off |
| Tech lead / architecture | Technical direction, design review, code standards, cross-team interfaces | Decision records (ADRs); C4 or similar diagram levels; design around likely change (Parnas); review designs before build; limit work in progress | Architecture diagrams, ADRs, interface contracts, coding standards |
| Frontend engineering | Browser UI, client state, accessibility, client performance | WCAG 2.2 AA; Core Web Vitals budgets; component libraries and design tokens; semantic HTML; unit plus component tests | UI components, design-system code, performance and accessibility reports |
| Backend engineering | APIs, business logic, data access, integrations | Contract-first APIs (OpenAPI); versioned endpoints; idempotent operations; input validation at boundaries; twelve-factor configuration | Services, API specs, migrations, integration tests |
| Mobile engineering | iOS and Android apps, offline behavior, store releases | Apple HIG and Material Design; OWASP MASVS; device/OS test matrix; remote feature flags; crash-free rate tracking | App builds, store listings, release notes, crash and performance dashboards |
| Embedded / firmware engineering | Device software, hardware interfaces, update mechanism | MISRA C/C++ or CERT coding standards; static analysis; hardware-in-the-loop tests; A/B firmware images; IEC 62304 or ISO 26262 where safety applies | Firmware images, hardware interface specs, HIL test results |
| UX design | User research, flows, interaction and visual design, usability | Research before design; usability testing with real users; accessible design (WCAG); shared design system; specs handed off with states and edge cases | Research findings, user flows, prototypes, design specs |
| Technical writing | User, API, and operational documentation | Diataxis structure (tutorial, how-to, reference, explanation); docs-as-code in version control; style guide; docs reviewed with code changes | User guides, API reference, release notes, runbooks (with SRE) |

### C2. Quality, platform, security, and data roles

| Role | Responsibilities | Best practices | Outputs |
| --- | --- | --- | --- |
| QA / SDET | Test strategy, automation, release quality gates | Test pyramid (most tests at unit level); risk-based test selection; tests in CI on every change; flaky-test quarantine with owners; ISTQB terminology | Test strategy, automation suites, defect reports, test summary per release |
| DevOps / build and release | CI/CD pipelines, build reproducibility, release automation | Build once, promote the same artifact; trunk-based development; pinned dependencies; DORA metrics (deploy frequency, lead time, change failure rate, recovery time) | Pipelines, build scripts, release artifacts, deployment logs |
| Platform / infrastructure | Compute, networking, environments, internal developer platform | Infrastructure as code; immutable infrastructure; self-service paved paths; least-privilege access; cost tagging | IaC modules, environment definitions, platform docs, access policies |
| SRE | Availability, observability, incident response, capacity | SLOs and error budgets; alerts tied to user impact; blameless postmortems; toil budgets (Google SRE: under 50%); load and chaos testing | SLO definitions, dashboards, alert rules, runbooks, postmortems |
| Security engineering | Threat modeling, secure SDLC, vulnerability management, compliance controls | NIST SSDF (SP 800-218); OWASP Top 10 and ASVS; STRIDE threat models; SAST, DAST, and dependency scanning in CI; SLSA for supply chain | Threat models, scan reports, security requirements, vulnerability tracker, audit evidence |
| Data engineering | Pipelines, warehouses, data quality, lineage | Idempotent, re-runnable pipelines; data contracts with producers; schema versioning; automated quality checks; lineage tracking | Pipelines, data models, quality dashboards, data catalog entries |
| Database engineering / DBA | Schema design, performance, backup and recovery | Normalize to 3NF unless a measured need says otherwise; backward-compatible migrations; tested restores, not just backups; defined RPO and RTO | Schemas, migration scripts, backup and restore procedures, performance reports |
| ML / AI engineering | Model training, evaluation, deployment, monitoring | Versioned data, features, and models; fixed evaluation sets with thresholds; model cards; drift monitoring; NIST AI RMF for risk | Trained models, evaluation reports, model cards, serving endpoints, drift dashboards |

## Sources

Cited from general knowledge, not verified against the texts for this draft. Numeric thresholds in this book (PR size, debt share, halt criteria) are example defaults, not values from these sources.

- Brooks, F. *The Mythical Man-Month* (1975; 1995 edition with "No Silver Bullet").
- Parnas, D. "On the Criteria to Be Used in Decomposing Systems into Modules." *CACM*, 1972.
- Dijkstra, E. "On the role of scientific thought" (EWD447), 1974.
- Hunt, A., and Thomas, D. *The Pragmatic Programmer* (1999; 20th anniversary edition 2019).
- Beck, K. *Extreme Programming Explained* (1999).
- Boehm, B. "A Spiral Model of Software Development and Enhancement." *IEEE Computer*, 1988.
- Forsgren, N., Humble, J., and Kim, G. *Accelerate* (2018).
- ISO/IEC/IEEE 12207 (software life cycle processes) and 29148 (requirements engineering).
- IEEE Computer Society. *SWEBOK Guide*, v4.0 (2024).

* Beyer, B., et al. *Site Reliability Engineering* (Google, 2016): SLOs and error budgets (Appendix B5).
* Shostack, A. *Threat Modeling: Designing for Security* (2014): STRIDE (Appendix B1).

- Standards named in Appendix C: W3C WCAG 2.2; OWASP Top 10, ASVS, and MASVS; NIST SP 800-218 (SSDF) and AI RMF 1.0; SLSA; MISRA C/C++; IEC 62304; ISO 26262; OpenAPI; Diataxis; DORA metrics; Mitchell et al., "Model Cards for Model Reporting" (2019).
