# project.json reference

The stage skills carry the procedure; the commands, paths and thresholds come from
`.claude/project.json` in each project. A `{{key}}` in a skill resolves from it.

```json
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src tests docs",
  "build_command": "<what proves a phase compiles on its own>",
  "build_manifest": "<file the build enumerates sources in, or none>",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "release_build_command": "<production-config build, or none>",
  "secret_scan_command": "<secret scanner: patch on stdin, SARIF on stdout, or none>",
  "sast_command": "<static analyzer writing SARIF 2.1.0 to stdout, or none>",
  "clean_build_command": "<build from a fresh checkout, dependencies included, or none>",
  "interface_docs": "<directory holding interface definitions, e.g. docs/api, or none>",
  "pr_review_limit_lines": 400,
  "unit_test_scope": "<the whole target, or the changed workspaces — and why>",
  "post_fix_verification_scope": "<what a fix commit must re-run before the gate passes>",
  "results_file": "<path the local gate writes its verdict to>",
  "results_read_command": "<command that reads counts out of it>",
  "integration_test_command": "<command that runs the integration suite, or none>",
  "integration_results_file": "<path that suite writes its verdict to, or none>",
  "integration_results_read_command": "<command that reads counts out of it, or none>",
  "system_test_command": "<command that runs the system suite on a release candidate, or none>",
  "system_results_file": "<path that suite writes its verdict to, or none>",
  "system_results_read_command": "<command that reads counts out of it, or none>",
  "nfr_test_command": "<command printing one <KEY> NFR<n> pass|fail line per NFR, or none>",
  "release_dir": "<directory for test summaries and release notes, e.g. docs/releases, or none>",
  "release_artifact_command": "<command that builds the release artifact and prints its path last, or none>",
  "deploy_command": "<command taking <stage> <artifact-path>, or none>",
  "smoke_test_command": "<command taking <stage>, exiting non-zero on failure, or none>",
  "rollback_command": "<command taking <stage>, or none>",
  "rollout_stages": ["<first production stage, e.g. canary>", "<next, e.g. all>"],
  "halt_criteria": ["<shell command exiting non-zero when its criterion fires>"],
  "monitoring_window_minutes": 60,
  "released_status": "<Jira transition and status released tickets move to, or none>",
  "ci_results_artifact": "<name of the uploaded CI result artifact, or none>",
  "ci_integration_results_artifact": "<name of the uploaded CI integration result artifact, or none>",
  "verification_tiers": "<the tiers an AC can be verified by>",
  "verification_step_file": ".claude/gates/<what ship-pr must resolve>.md",
  "failure_policy_gate": ".claude/gates/<gate holding the failure policy>.md",
  "mechanics_gate_dod": ".claude/gates/dod-mechanics.md",
  "mechanics_gate_pre_push": ".claude/gates/pre-push-mechanics.md",
  "registry_file": ".claude/registries.md",
  "plan_rules_file": ".claude/plan-rules.md",
  "brief_file": "docs/brief.md",
  "user_docs_targets": "README.md docs/user-guide.md",
  "extra_gates": [".claude/gates/<project-only gate>.md"],
  "reviewers": "<comma-separated GitHub logins or org/team slugs, or none>",
  "merge_method": "<merge, squash, or rebase>",
  "done_transition": "<name of the Jira transition into the done state>",
  "incident_reviews_dir": "<directory incident reviews are committed to, e.g. docs/incidents, or none>",
  "iteration_days": 14,
  "debt_share_target": "<percent of resolved issues that should be preventive, e.g. 15, or none>",
  "dependency_outdated_command": "<command listing outdated dependencies, e.g. npm outdated, or none>",
  "patch_sla_days": "<days a vulnerability may stay unpatched, e.g. 30, or none>",
  "runbooks_dir": "<directory holding the runbooks, e.g. docs/runbooks, or none>",
  "alert_routes_command": "<command printing one `<rule> <target>` line per alert route, or none>",
  "retirements_dir": "<directory retirement records are committed to, e.g. docs/retirements, or none>",
  "design_dir": "<directory feature design docs are committed to, e.g. docs/design, or none>",
  "adr_dir": "<directory decision records are committed to, e.g. docs/adr, or none>"
}
```

A key naming a file the project does not have gets `none`, and the skill says so in one
line rather than inventing a substitute. `verification_step_file` is the one that matters
most: it is where `ship-pr` learns whether this project's diff needs a push-run suite, a
session on real hardware, or nothing beyond the checklist — the single biggest divergence
between projects.

`reviewers` serves rule book R2: every change is reviewed by someone other than its author.
It is a comma-separated list of GitHub logins or `org/team` slugs, the form
`gh pr edit --add-reviewer` takes. `ship-pr` requests them on the PR, leaving out the PR's
author, and `ci-green` does not finish until someone other than the author approves the
PR's latest commit. Default `none`: no reviewer is requested, and `ci-green` instead records
an R2 exception in `exceptions_log`, pausing once for the tech lead to approve it, unless an
unexpired R2 row already covers the run. With `exceptions_log` also `none`, it stops and
asks. The wait only keeps the run open. `ci-green` merges only on the tech lead's yes, and
on the exception path that yes merges a PR nobody reviewed; what stops anyone else's
unreviewed merge is a branch protection rule or ruleset requiring an approval of the latest
push.

`merge_method` and `done_transition` serve rule book Phase 4 step 9: merge, and delete the
branch. `merge_method` is `merge`, `squash`, or `rebase`, default `squash` — the
`gh pr merge` flag `ci-green` uses once the tech lead says yes; any other value stops the
run. `done_transition` names the Jira transition that then moves each covered ticket to
done, default `Done`. The checks before the merge, and the decline and failure paths, are in
`skills/ci-green/SKILL.md` Step 5. A rule requiring an approval refuses the merge on the R2
exception path, which has none; the tech lead then merges outside the run.

`incident_reviews_dir` serves rule book Phase 7 step 3: where `incident-review` commits each
review. It must be a relative path inside the repository, outside `.git`, starting with a
letter, digit, or `_` and made only of letters, digits, `.`, `_`, `-`, and `/`, and not
gitignored, since the review is committed.
Default `none`, under which `incident-review` stops and names the key.

`iteration_days`, `debt_share_target`, `dependency_outdated_command`, `patch_sla_days`,
`runbooks_dir`, and `alert_routes_command` serve rule book Phase 7 steps 2, 4, 5, and 6 and
its ongoing checks, in `maintenance-review`. `iteration_days` is a whole number of days,
default `14`, over which the share of resolved issues labeled `preventive` is measured;
`debt_share_target` is the percent, from 0 to 100, that share should reach — the rule book
calls 10–20% "a common starting point" and leaves the figure to the project. `patch_sla_days`
is the whole number of days an open Dependabot alert may age before it is past its SLA.
`runbooks_dir` follows `incident_reviews_dir`'s path rule and needs a full clone, since a
shallow one gives every file the boundary commit's date; a runbook's age is from the last
commit touching it, a rename or reformat included. `alert_routes_command` prints one
`<rule> <target>` line per alert route, read against `on_call`. Each defaults to `none`,
under which its section of the report says it is unset, except `iteration_days`, and
except that `security` makes `patch_sla_days` required.

`retirements_dir` serves rule book Phase 7 step 7: where `retire-system` commits each
retirement record. It follows `incident_reviews_dir`'s rule — a relative path inside the
repository, outside `.git`, of the same characters, and not gitignored, since the record is
committed. Default `none`, under which `retire-system` stops and names the key.

`design_dir` and `adr_dir` serve rule book Phase 3 and R11: where a feature's design doc
and its decision records are committed. Each follows `incident_reviews_dir`'s rule — a
relative path inside the repository, outside `.git`, of the same characters, and not
gitignored, since both are committed. Each defaults to `none`.

`secret_scan_command` and `sast_command` serve rule book R12 and Appendix B1's scans. Each
writes SARIF 2.1.0 to standard output, redacted, with inline suppression comments ignored;
`gates/scripts/sarif_gate.py` builds what each scanner reads from git and turns the reports
into the gates' verdicts. The secret scanner reads added lines as a patch on standard
input —
`gitleaks stdin --redact --ignore-gitleaks-allow --report-format sarif --report-path /dev/stdout`
is one that does, and a scanner that only reads files is wrapped to read `/dev/stdin`. The
static analyzer runs from a tree's root, e.g. `semgrep scan --sarif --disable-nosem`. The
bars are in `gates/definition-of-done.md`; the pre-push checklist runs both again, feeding
the secret scanner each commit's message with its patch. Both default to `none`, and a
skipped scan is announced.

`clean_build_command` serves rule book R10: the one documented command that builds the
project from a clean checkout. It installs in the ecosystem's locked mode — `npm ci`,
`cargo build --locked`, `uv sync --locked` — so a lockfile that disagrees with its manifest
fails the build rather than being rewritten. The pre-push checklist runs it in a fresh
`git worktree` of HEAD, which holds no submodules, so a project with them initializes them
in this command. Default `none`, announced as skipped.

`interface_docs` serves rule book R3: where a project keeps its interface definitions —
OpenAPI specs, schemas, CLI references. Check 7 in `gates/rule-book-review.md` says when a
definition must change with its interface. Default `none`, under which every definition is
the doc comment at the interface's declaration.

`brief_file` serves rule book Phase 1: the path of the project brief. `plan-project` writes
it — problem, users, goals, non-goals, numeric success measures, constraints, five owned
risks, lifecycle, and an estimate range — checks the build and the parent branch's CI
against `gates/planning-exit.md`, stops for the sponsor, then records the decision and
commits the brief on `brief/<slug>`, which reaches the parent branch by an ordinary pull
request. `write-tickets` traces its `Goal:` lines to an approved brief's goals wherever
the checkout holds it, and removes work serving none; with `brief_file` set it stops on any brief not approved
or naming no goal, sending a pending one to the sponsor through `plan-project`. The brief is committed, so the path
must not be gitignored. Default `none`, under which `plan-project` stops and
`write-tickets` reads no goals.

`pr_review_limit_lines` serves rule book R9: a pull request reviewable in under an hour. It
caps one PR's changed lines, insertions plus deletions against the parent branch.
`plan-work` sizes its phases to it, and the pre-push checklist checks it before every push,
asking you when the diff is over; a yes records the count as `pr_size_approved_lines` in
`.claude/state/current-plan.json`, and it asks again only past that count, or at every push
without a state file for the branch. Default `400`, where review effectiveness falls off
in SmartBear's study of code review at Cisco; `none` skips the check, announced as skipped.

`integration_test_command` serves rule book Phase 5 step 1: integration tests across module
interfaces and external services, run on every pull request. The pre-push checklist runs it
after the unit suite, writing `integration_results_file` and reading its counts with
`integration_results_read_command` — a file and a reader of its own, as Maven's Failsafe
writes and reports integration results apart from Surefire's unit results, so neither suite
overwrites or misreads the other's verdict. The Definition of Done never runs it, so a third
party being down never blocks a commit. All three default to `none`, announced as no
integration tier; with the command set, the push stops before running it while either of
the other two is `none` or the results file is `results_file`. In CI, `ci-green` reads a
failing integration job from `ci_integration_results_artifact` with the same integration
reader, as `ci_results_artifact` serves the unit job; default `none`, which leaves that
job's log as its only evidence. Each artifact is downloaded into a fresh directory and its
result file moved over its suite's deleted results file, so neither a local run's verdict
nor an earlier download is read as CI's. It stops and names the key
when either artifact is set with its reader or results file `none`, the integration
artifact is set with no integration command, or the two artifacts or results files
coincide.

`system_test_command`, `system_results_file`, `system_results_read_command`,
`nfr_test_command`, and `release_dir` serve rule book Phase 5, whose gate is
`gates/release-readiness.md`. The system suite runs end-to-end flows in a production-like
environment on every release candidate. It writes its own results file, read by a reader of
its own, as the integration suite does. `nfr_test_command` takes no arguments and prints one
`<KEY> NFR<n> pass` or `<KEY> NFR<n> fail` line per `- NFR<n>:` threshold it checks. How
those lines, and an `exceptions_log` row for one, settle the gate is criterion 3 of
`gates/release-readiness.md`. Each Must acceptance criterion is listed, with its `[verify:]`
tier, which `verification_tiers` must declare, under the summary's `Untested requirements`
for the product owner's acceptance, per criterion 1. It reads `verification_tiers` as tier
names separated by `·`, commas, or semicolons, each optionally in backticks and followed by
a note in parentheses; `and` and `or` are joiners, and names compare without case.
`release_dir` holds each version's test summary, its note file, the Must tickets'
description copies the check reads, the release notes, and with disciplines named, the
model thresholds, the error-budget reading, and the security sign-off. They are working files, not
committed, so the path may be gitignored. The note `release-readiness` writes on the tested
commit under `refs/notes/release-readiness`, which `release` checks and pushes with the tag,
records the summary's hash and verdict there; it is an integrity check, not a signed
attestation. The hosted equivalents, a GitHub commit status or check run for the verdict and
Environment required reviewers for the stage approvals, are a known deviation: both skills
keep their records in git and the session, so they run the same without GitHub's protections
configured; so is the security sign-off, recorded only in its `release_dir` file. Every
configured command runs in a subshell from the project root, and one that takes arguments
receives them at its end, so in a pipeline only the last command gets them; wrap a pipeline
in a script that passes them on. All five default to `none`. A `none` system key or
`release_dir` stops `release-readiness` and names the key, and so does a system results
file equal to `results_file` or `integration_results_file`.

`release_artifact_command`, `deploy_command`, `smoke_test_command`, `rollback_command`,
`rollout_stages`, `halt_criteria`, `monitoring_window_minutes`, and `released_status` serve
rule book Phase 6, whose gate is `gates/release.md`. `release` builds the artifact once,
from a worktree of the new `v<version>` tag, with `release_artifact_command` — the
deployable artifact itself, where `release_build_command` only proves a production-config
build compiles before a push — and takes the last line the command prints as its path. Every
stage deploys that path with `deploy_command <stage> <artifact-path>`, checks it with
`smoke_test_command <stage>`, and undoes it with `rollback_command <stage>`; staging's
rollback is tested before any production stage. `rollout_stages` lists the production stages
in order. `halt_criteria` lists shell commands that each exit non-zero when their criterion
fires — an error rate above 1%, say, or p95 latency 20% above baseline, the rule book's
examples — and every one runs once a minute for `monitoring_window_minutes` after each
stage. `released_status` names the Jira transition the released tickets take, matched by
name and confirmed by reading each ticket back. All default to `none` except
`monitoring_window_minutes`, which defaults to `60`, the rule book's one hour. What stops
`release` before it tags, including `rollout_stages` `none` on a `medium` or `large`
project, is listed once, in `gates/release.md`. `released_status` `none` leaves the
tickets where they are.

The values in the block above are illustrations, not defaults. Some of its keys are
required and have no default; one that is missing, empty, `none`, or a `<placeholder>`
stops the run. Any other key absent from
project.json resolves to the default this file gives it, or to `none` where it gives
none. `extra_gates` defaults to `[]`. `gates/project-config.md` names the required keys
and holds the procedure every skill and agent follows, including how a run reports the
value each absent key took.

Two keys exist because projects hold genuinely different policy on the same question,
and each states its reasoning rather than just its answer. `unit_test_scope` is the
whole-target-versus-changed-workspaces trade: matching CI exactly, against a suite slow
enough that the cost is real. `post_fix_verification_scope` is whether a fix commit
restarts the push gate — a project whose selector resolves a diff to affected tests can
re-run that set and have a real verdict; one without a selector has no such answer and its
only honest re-verification is everything.

Six more keys tailor the workflow to the project, per the rule book's "Tailoring and
exceptions" section and its Appendices A through C, and the block also holds the keys
`disciplines` brings in. The six are optional, and each bullet below gives its default;
the `roles`, `on_call`, and `exceptions_log` values are placeholders, not defaults. The
keys between `disciplines` and `roles` in the block are its addenda's: required once their
discipline is named, with no default, and placeholders here.

```json
{
  "project_size": "small",
  "lifecycle_model": "continuous",
  "disciplines": [],
  "data_quality_command": "<command exiting non-zero when a data-quality check fails>",
  "model_eval_command": "<command reading <metric> <minimum> lines on stdin, exiting non-zero below one>",
  "model_eval_thresholds": ["<metric> <minimum>, e.g. precision 0.92>"],
  "drift_check_command": "<command printing the current drift as one number>",
  "drift_threshold": "<number above which drift triggers retraining or rollback, e.g. 0.25>",
  "device_matrix": ["<os> <version>, e.g. ios 16.4>", "<os> <version>, e.g. android 10>"],
  "device_test_command": "<command taking <os> <version>, exiting non-zero on failure>",
  "hil_test_command": "<command running the hardware-in-the-loop suite, exiting non-zero on failure>",
  "security_sensitive_paths": "<space-separated CODEOWNERS-style patterns, e.g. src/auth/ *.pem>",
  "api_compat_command": "<command taking the minimum app version, exiting non-zero when the API breaks it>",
  "min_supported_app_version": "<oldest app version still supported, e.g. 4.2>",
  "error_budget_command": "<command printing the remaining error budget as one number>",
  "alert_rules_dir": "<directory holding the Prometheus alerting rules, e.g. ops/alerts>",
  "roles": {
    "sponsor": "<handle>",
    "product_owner": "<handle>",
    "tech_lead": "<handle>",
    "qa": "<handle>",
    "release_manager": "<handle>",
    "security": "<handle>",
    "service_owner": "<handle>"
  },
  "on_call": ["<handle>", "<handle>"],
  "exceptions_log": "<path to the project's rule-book exceptions register>"
}
```

- `project_size` — `small`, `medium`, or `large`. Default `small`.
- `lifecycle_model` — `waterfall`, `iterative`, or `continuous`. Default `continuous`.
- `disciplines` — a list drawn from `security`, `data-ml`, `mobile`, `embedded`, and
  `sre`. Default `[]`. With `security`, `plan-work` requires a STRIDE `## Threat model`
  in every plan, and `design-adversary` blocks a `High` threat that names no phase.
  `write-tickets`' linter requires rule book Appendix B's ticket fields: with `data-ml`, a
  `## Data` section on a Story labeled `data` and a holdout NFR on one labeled `model`; with
  `embedded`, memory, power and timing NFRs on an Epic; with `sre`, an `over <n> days`
  window on an availability or latency NFR. With `data-ml`, `plan-work`'s `## Data
  ownership` names each dataset's schema owner and version location, and `design-adversary`
  flags a plan without them. `plan-work`, `write-tickets`, `release-readiness`, and `release`
  stop on any other name, matched with case, since a misspelled discipline would skip its
  addenda without a word. A named discipline
  adds its sections of `gates/release-readiness.md` and `gates/release.md`, where it has
  them, and a discipline left out skips them silently. The keys a named discipline needs at a gate
  have no default: absent, `none`, a `<placeholder>`, or malformed, they stop that gate's skill.
  - `data-ml` at readiness: `data_quality_command` and `model_eval_command`, each exiting
    non-zero on failure. `model_eval_thresholds` is a list of `<metric> <minimum>` pairs, the
    minimum a decimal number and each metric named once, without regard to case; the model
    command reads them as lines on standard input and exits non-zero when any metric falls
    below its minimum.
  - `mobile` at readiness: `device_matrix` is a list of `<os> <version>` entries, the
    version dotted digits, e.g. `ios 16.4`. `device_test_command <os> <version>` runs once
    per OS, on its lowest version, compared as numbers, so `ios 9` is older than `ios 10`.
    OS names compare without case, so `iOS 17` and `ios 15` are one OS.
  - `embedded` at readiness: `hil_test_command` runs the hardware-in-the-loop tests on
    target hardware; simulator results alone do not meet rule book Appendix B4. At release,
    the release manager confirms the artifact installs atomically with a fallback image.
  - `security` at release: `security_sensitive_paths` is a space-separated list of globs, read
    as CODEOWNERS reads its patterns — `*.pem` matches at any depth, `/keys/` only at the
    root, `src/auth/` everything below it, `docs/*` only directly in `docs/`. A `!`
    negation, a `[ ]` range, or a `\` escape stops the release, since CODEOWNERS supports
    none of them. A path the release's range changed that matches one, deleted or moved
    included, needs the security role's sign-off before the tag.
  - `mobile` at release: `api_compat_command <min_supported_app_version>` exits zero when the
    server API still serves that app version, the version dotted digits. `rollout_stages`
    must list at least two stages, the store's phased release, whatever `project_size` is,
    and `rollback_command <stage>` halts that phase. The release notes gain `## Remote
    flags`, one line per ticket, from `Remote-flag: <flag>` git trailers on its commits —
    a trailer the commit that adds the behavior carries — or, for a ticket with none, from
    the release manager's answer: the flag, or `none — <reason>`.
  - `sre` at release: `error_budget_command` prints the remaining error budget as one
    number. At `0` or below, the release stops unless every ticket in scope carries the
    `reliability` label.
  - `security` at maintenance: `patch_sla_days` is required, and `maintenance-review` lists
    the Critical alerts past it in their own section, Appendix B1's patch rule.
  - `data-ml` at maintenance: `drift_check_command` prints the current drift as one decimal
    number, and `drift_threshold` is a JSON number; drift above it is reported, Appendix B2's
    trigger for retraining or rollback.
  - `sre` at maintenance: `alert_rules_dir` holds Prometheus rule files or
    prometheus-operator `PrometheusRule`s, relative to the repository as `incident_reviews_dir`
    is. `maintenance_check.py alert-rules` reports each alerting rule naming no SLO — an `slo`
    or `sloth_slo` label or annotation — or no runbook — a non-blank `runbook_url` or
    `runbook` annotation — saying which it lacks. Appendix B5 asks that every alert map to
    an SLO or a documented failure mode and link to a runbook; an alert mapped to a failure
    mode instead is listed `no SLO` for the service owner to judge.
- `roles` — a map from each role above to the person who holds it. `{{roles.<role>}}` in a
  skill resolves to that role's entry in `roles`, so `{{roles.tech_lead}}` names the tech
  lead. `plan-project` waits on the sponsor, `write-tickets` on the product owner after QA
  confirms each `Must` ticket's ACs are testable, `release-readiness` on the product
  owner's review of the test summary, `release` on the release manager before staging and
  before each production stage, `plan-work` on the tech lead after QA approves the test
  strategy, `ship-pr` hands QA the verification charter, `incident-review` and
  `maintenance-review` wait on the service owner before creating a ticket, `retire-system`
  before marking each section done, and `ci-green` and `deliver` send rule-book exceptions
  to the tech lead, as `ci-green` does the merge question. Default: a role absent from
  `roles` is the person running the session, and the skill addresses that person directly.
  That is the absent-key rule above applied per role, so a missing role never resolves to
  `none`, and a project with no `roles` key at all has the person running the session in
  every role.
- `on_call` — the handles of the people on the on-call rota, each one word. A route from
  `alert_routes_command` reaches a person only when its target equals one exactly, case
  included. Default `none`, under which `maintenance-review` reports the rota unset and every
  route as reaching no person.
- `exceptions_log` — the project's register of rule-book exceptions, in the format
  `gates/exceptions.md` defines. Default `none`, under which a run stops rather than skip
  a "must" step.
