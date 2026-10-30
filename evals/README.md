# Eval suite

Behavioral tests for the kit's skills and agents. CI checks that the kit's files are
*well-formed*; this suite asks whether the skills still *do what they claim*.

```bash
claude plugin eval . --scaffold
```

`--scaffold` runs the `scaffold.sh` of each case with a `context.scaffold_script`. Those
cases need it to write their `project.json`; without it they run in an empty workspace and
fail.

`allowed_tools` grants only read-only tools. A case that lists `Bash`, `Write`, `Edit`,
`WebFetch`, or `WebSearch` gets them only from `--allow-tools`, so a skill that writes a
file fails every with-arm run without `Write`. Pass exactly what each case lists:
`plan-project-stops-at-approval`, `design-feature-stops-at-approval`,
`design-feature-reopens-an-accepted-design`, `readme-docs-updates-an-existing-readme`, and
both `release-*` cases list `Bash`, `Write`, and `Edit`
(`release-readiness-stops-without-system-suite` all but `Edit`); the adversary
cases' commands appear with them below. For example:

```bash
claude plugin eval . --scaffold --case plan-project-stops-at-approval --allow-tools Bash Write Edit
```

Each case runs with and without the plugin loaded, three times by default, so the report
shows what the plugin contributes rather than what the model would have done anyway.

## Why these cases

The kit's own doctrine is that a guard whose only failure mode is silence is worse than
no guard. That principle is applied rigorously to the two hooks — 77 and 40 self-test
cases asserting exact counts — and was applied nowhere to the skills. Each case here
targets a behavior whose absence produces a *plausible run* rather than an error:

| Case | What its silent failure looks like | Δ |
| --- | --- | --- |
| `deliver-reads-stage-files` | A run following a remembered approximation of a stage rather than the stage | +1.00 |
| `refuses-without-project-json` | Invented build and test commands that run something other than what the project uses | +0.50 |
| `plan-work-stops-at-approval` | Planning that quietly starts implementing — the approval gate is the one hard stop in the workflow | +0.17 |
| `plan-project-stops-at-approval` | A brief that records the sponsor's decision itself, or branches and commits before the sponsor answers | not yet measured |
| `design-feature-stops-at-approval` | A design that records the tech lead's decision itself, or writes, branches, or commits beyond the design doc and its ADRs before the approvals are given | not yet measured |
| `design-feature-reopens-an-accepted-design` | A design accepted on `main` that needs rework is reverted by hand on `main` and pushed, since nothing offers a branch to reopen it on | not yet measured |
| `release-readiness-stops-without-system-suite` | A test summary, with a `Gate:` verdict, written for a project that has no system suite to run | not yet measured |
| `release-asks-before-staging` | A release that deploys to staging on the strength of the request itself, before the release manager approves | not yet measured |
| `write-tickets-hands-a-proposed-design-back` | A design reopened by hand on `main` gets contradictory directions, each skill pointing at the other, rather than one `NEXT:` command | not yet measured |
| `write-tickets-stops-without-config` | Tickets drafted against verification tiers and source roots the project never declared | +0.50 |
| `design-adversary-passes-a-sound-plan` | Review that always finds a blocker, so planning always ends in deferred work | not yet measured |
| `design-adversary-catches-a-missing-ac` | Review that stopped blocking real defects after its BLOCKER definition was narrowed | not yet measured |
| `design-adversary-catches-an-unmapped-nfr` | A plan that phases every NFR but never says which design element meets one, or leaves an affected Epic NFR unphased, passes review | not yet measured |
| `design-adversary-flags-incomplete-design-sections` | A plan whose interfaces, likely changes, NFR rows, or new dependencies are incomplete passes review, because no finding can cite code | not yet measured |
| `design-adversary-catches-an-unmitigated-threat` | A plan under the security discipline rates a threat `High` and names no phase that mitigates it, and review passes it | not yet measured |
| `design-adversary-flags-missing-dataset-ownership` | A plan under the data-ml discipline names no schema owner or version location for its dataset, and review passes it | not yet measured |
| `design-adversary-flags-an-unsurveyed-design` | A plan that cites a source for each piece of the ticket's design passes, though nobody asked how real systems solve the whole problem | not yet measured |
| `readme-docs-updates-an-existing-readme` | An update that regenerates the README from the template, dropping custom sections and carrying stale versions over | not yet measured |
| `stops-on-missing-required-key` | A guessed parent branch that the run then branches from and pushes against | +1.00 |
| `announces-missing-optional-keys` | An invented registry or rules path, or optional keys that quietly read as nothing | not yet measured since its grader gained `pr_review_limit_lines`, `roles`, `design_dir`, and `adr_dir` |
| `ci-failure-adversary-requires-a-named-test` | A correct source fix whose commit message names no test passes review, so the defect-fix gate holds only on the author's word | not yet measured |
| `ci-failure-adversary-passes-a-tested-fix` | Review that returns `UNVERIFIED` for every fix, so ci-green can never close a failure | not yet measured |
| `ci-failure-adversary-rejects-an-import-only-test` | A named test red on the parent only because it imports a new symbol verifies a fix it never exercises | not yet measured |
| `feature-design-adversary-catches-a-missing-rollback` | A design whose rollout step can't be undone passes review, so the gate's rollback rule holds only on the author's word | not yet measured |
| `feature-design-adversary-passes-a-sound-design` | Review that blocks every design, so no feature ever clears the design-exit gate | not yet measured |

Each case should pair a check on the *result* with a check on *how Claude got there*, per
the official guidance: a `regex` or `llm` grader on the reply, and a `tool_used` grader on
the transcript. The two missing-key cases, `readme-docs-updates-an-existing-readme`,
`plan-project-stops-at-approval`, `design-feature-stops-at-approval`,
`design-feature-reopens-an-accepted-design`, `release-asks-before-staging`,
`release-readiness-stops-without-system-suite`, all three `ci-failure-adversary-*`
cases, and both `feature-design-adversary-*` cases do.
`write-tickets-stops-without-config` has a `tool_used` grader that cannot fail, since Write
is not in its allowlist, and `refuses-without-project-json` and all seven `design-adversary-*`
cases grade the reply only.

**Δ is the number that matters, not the score.** A case scoring 1.00 in both arms is
measuring what the model already knew. The deltas above are from the run of
2026-09-14 against Opus 5, except `stops-on-missing-required-key` and the two project.json
rows (`refuses-without-project-json`, `write-tickets-stops-without-config`), measured
2026-10-11 against Opus 5.5; re-measure rather than trusting them after a model change.
The missing-key row's +1.00 is partly by construction, since the baseline has no gate to
read, so its meaningful comparison is against `main`'s skills, below.

`plan-project-stops-at-approval` needs GitHub, which the sandbox lacks: `plan-project`
stops unless the parent branch's latest CI run reports `success`. Its scaffold builds a
repo whose `origin` is a local bare clone, so `git fetch` can succeed offline, and its prompt
supplies the `gh run list` output as retrieved evidence, as the `ci-failure-adversary-*`
prompts do, so the run reaches the sponsor stop the case exists to test. Whether that
fetch runs on macOS is not yet re-measured; see the sandbox's `git` limit below.

`design-feature-stops-at-approval` scripts each earlier answer the run would otherwise stop
for. Its prompt reproduces the survey sources, since web search and Jira are unavailable,
and answers step 8's question for outside reviewers with none; its scaffold's
`exceptions_log` holds an unexpired step 8 row, so exit criterion 1 can pass, and its
`.claude/agent-rules/feature-design-adversary.md` tells the dispatched reviewer that a
source it cannot reach is UNVERIFIABLE. The run then reaches Step 5's approvals. A run
that stops at Step 4's review cap instead fails `waits-for-approval` too, so read a failed
run's reply before scoring it as a gate failure, as for one that runs out of its 60 turns
during review. The skill writes the design doc and its input files with Write and revises
them with Edit, and the session and the dispatched `feature-design-adversary` run git
through Bash, so grant all three. Whether the transcript records the
reviewer's calls is unconfirmed, as for the `ci-failure-adversary-*` cases below; the one
command the reviewer prescribes, its `git fetch` and `adr_numbers.py` check, matches neither
`no-shell-writes` nor `no-branch-or-commit`. `creates-the-design` and `creates-nothing-else`
read the paths the run created, so they catch a write the transcript graders cannot see:

```bash
claude plugin eval . --scaffold --case design-feature-stops-at-approval --allow-tools Bash Write Edit
```

`plan-work-stops-at-approval` sits at +0.17 because its `no-branch-created` grader passes
trivially in the baseline — an arm with no plugin has no reason to run git either. The
grader still earns its place: it caught the with-arm reaching for Bash during planning,
which is a real finding about the skill rather than about the suite.

### `design-adversary-passes-a-sound-plan` is a false-positive case

Every other case here asks whether a stage does something. This one asks whether a stage
**stops doing something** — whether a reviewer told to find reasons a plan will fail can
return nothing when there is nothing to find. That failure is silent in the worst way: a
review manufacturing blockers looks exactly like a thorough review, and the plan skill then
resolves them the only way it can, by deferring work into tickets nobody asked for.

The plan in the prompt is deliberately sound and deliberately ordinary — a bounded retry
with backoff, an extraction of an existing in-repo implementation, one justified exclusion.
It is the kind of plan that should sail through, and before the reviewer's rules were made
conditional on evidence, plans of this shape did not.

**Its known weakness is the arms.** Neither arm reaches `agents/design-adversary.md`, as
[Reaching an agent's definition](#reaching-an-agents-definition) explains, so both review
with no instructions at all and may well return zero BLOCKERs by default. Until the case
dispatches the agent, a score here says how an uninstructed reviewer behaves, not the
plugin. Read the findings themselves too: the graders check severity and remedy, and a
reply that passes both while listing useful MAJORs is the target behavior, not a near miss.

The case is also **not a regression test for under-reviewing**. Nothing here would catch a
reviewer that has stopped finding real blockers, because a sound plan gives it nothing to
miss. That is what `design-adversary-catches-a-missing-ac` is for, and **the two are read
together or not at all.**

That case plants one defect — ABC-207's fourth acceptance criterion, rate limiting, is in
the ticket and in no phase — and requires it back as a BLOCKER, not as a MINOR or a
question. BLOCKER is now five checkable things, narrowed from an open list — the largest
change made to the reviewer — and this is the case that says the narrowing cost nothing.

Passing one alone means little in either direction. A reviewer that blocks nothing passes
the sound-plan case and fails this one; a reviewer that blocks everything does the reverse.
Only both passing says the severity line sits where it was meant to.

`design-adversary-catches-an-unmapped-nfr` checks the fourth BLOCKER kind the same way: its
NFR2 has a phase but no `NFR coverage` row, and its parent Epic's NFR1 has no row at all,
so only that kind can block either. Its Epic's NFR2 has a row but no phase, the Epic half of
the first kind. Its
false-positive partner is again the sound plan, whose ticket NFR and parent Epic NFR both
have rows, the Epic's stating this branch leaves it untouched.
`design-adversary-flags-incomplete-design-sections` covers the design-sections MAJOR: five
incomplete entries, each required back as a MAJOR and none as a BLOCKER, beside an
`untouched` Epic row that must draw no finding at all.
`design-adversary-catches-an-unmitigated-threat` checks the fifth BLOCKER kind: its
webhook plan's `Threat model` rates Denial of service `High` with no phase, beside two
`High` rows that name Phase 1, a `Medium` row naming Phase 2, and `Low` rows with none,
each of which must draw no BLOCKER for its phase cell.

## Reaching an agent's definition

A case that tells the session to act as an agent and read `agents/<agent>.md` reaches
nothing: each run starts in an empty workspace, so that path is not there, and both arms
review with no instructions. The local runs of 2026-10-12 show it: across two
`design-adversary-*` cases, the reply says the definition could not be read in 35 of 36
runs, with-arm runs included. `results/` is not tracked, so re-run a case to check.

A case reaches an agent by dispatching it instead. The plugin registers its agents in the
with-arm only, so a baseline dispatch fails with `Agent type '<plugin>:<agent>' not found`,
and the agent reads the gates from the installed plugin. Its scaffold writes the
`project.json` and every input the agent reads, and its prompt hands the agent only the
refs its definition allows.

`feature-design-adversary-catches-a-missing-rollback` works this way. Its scaffold writes a
design doc that meets every rule of `gates/design-exit.md` but one: rollout step 3 names no
rollback step, BLOCKER kind 5. The prompt passes the agent the doc's absolute path and nothing
else, and `dispatches-with-the-path` checks that it did. The repository the design cites is
absent, which the scaffold's `.claude/agent-rules/feature-design-adversary.md` tells the
agent, so its `Current state` claims are UNVERIFIABLE. `dispatches-with-the-path` passes in
both arms, since a failed dispatch still records its input; the `llm` grader is what
separates them. The agent surveys the web and runs git, so grant those tools, and the
case's `timeout_seconds` of 900 gives it room. The scaffold makes no git history and no
`origin`, so the agent's `git fetch` always fails, and its step 7 then marks the claim UNVERIFIABLE.

`feature-design-adversary-passes-a-sound-design` is its false-positive partner, a contrast
set in the sense of Gardner et al. (2020): its scaffold writes the same doc with step 3's
rollback restored, so the two designs differ by that one line. A reviewer that blocks
nothing passes the sound case and fails the defective one; one that blocks everything does
the reverse. Only both passing says the BLOCKER line sits where it was meant to, and only
that one line can explain a verdict that differs between them. Its `zero-blockers` grader
names one BLOCKER it fails in particular, one raised because a file `Current state` cites is
missing: that is a claim the reviewer could not check, not one the code contradicts. Run
both:

```bash
claude plugin eval . --scaffold --case 'feature-design-adversary-*' --allow-tools Bash WebSearch WebFetch
```

The three `ci-failure-adversary-*` cases dispatch `delivery-kit:ci-failure-adversary` the
same way, with only the CI evidence, the note that it came from the run on `HEAD~1`, and the
ref `HEAD`. `dispatches-the-agent` checks that the delegation names the agent, carries the
`FAILED` line and the bare ref, and holds no common test-runner command; nothing checks the
rest of it. It passes in both arms, as `dispatches-with-the-path` does. Their
`runs-the-named-test` graders match a Bash call holding the test's run form, and
`reads-the-dod` a Read of the DoD. Each counts the session's calls and the dispatched
agent's alike. Whether a run's transcript records a subagent's calls, always or only
sometimes, is unconfirmed: no trace has been read. Until one is, a zero from either grader
may mean the transcript left the call out rather than that the agent skipped it. Nothing
checks that the named test ran on both the parent and the fix: the `llm` graders grade the
verdict, and `runs-the-named-test` cannot tell one run from the other. Each scaffold writes
`project.json` after the last commit, untracked, so it is not in the fix's diff. Two also
write `.claude/agent-rules/ci-failure-adversary.md`, the agent's rules file, saying how to
run a test without pytest. Run them with:

```bash
claude plugin eval . --scaffold --case 'ci-failure-adversary-*' --allow-tools Bash WebSearch
```

**The known gap is the seven `design-adversary-*` cases**, which still tell the session to
act as the agent, so neither arm reaches its definition. A dispatched `design-adversary`
reads its tickets from Jira, and a run has no Jira to reach: a mock answers only for an MCP
server the plugin declares, and this plugin declares none. Their scores measure an
uninstructed reviewer until that changes.

## What these cases cannot test

`tool_used: Skill` is the natural grader for "did the plugin fire", and it is
**unsatisfiable here** for the stage skills. Each carries `disable-model-invocation: true`,
so the model is structurally unable to invoke one; `readme-docs` does not, which is why its
case can grade on it. A slash command in a prompt body reaches the run as literal text
rather than as an invocation, since the harness sends the body exactly as written; the
`readme-docs` case names the plugin skill that way so the model loads it rather than a
same-named user-level copy.

What the with-arm measures instead is the plugin's *files being present, findable, and
followed*. That is a real difference — the baseline arm scores 0.00 on
`deliver-reads-stage-files` and costs nothing, because it has nothing to read — but it is
not proof that slash-command routing works. Nothing in this harness can prove that.

## What the sandbox allows, and what it rules out

Every run starts in an **empty workspace**. No project `.claude/`, no `CLAUDE.md`, no MCP
servers, no user settings. That constrains what can be tested here:

- **Testable**: whether a stage reads its files, whether it refuses without configuration,
  whether planning stops at the approval gate, the shape of what it produces.
- **Testable with a scaffold**: a workspace that needs only files or a local git history
  made before the run. The missing-key cases' `context.scaffold_script` writes a
  `.claude/project.json` and nothing else. Measured 2026-10-11 against the skills on `main`
  before `gates/project-config.md`, the required-key case scored 0.33 and the optional-key
  case 0.44, with no run passing, against 1.00 for both after it, 3 runs per arm. `results/`
  is not tracked, so re-run both against `main` and the branch to check these.
  The `feature-design-adversary-*` scaffolds write a `project.json`, the agent's rules file,
  and a design doc.
  `readme-docs-updates-an-existing-readme`'s scaffold writes a small Python project; the
  `ci-failure-adversary-*` cases, `plan-project-stops-at-approval`,
  `release-asks-before-staging`, and `release-readiness-stops-without-system-suite` build a
  git repo, the last three with a local bare `origin`; the `ci-failure-adversary-*` ones add
  an untracked `project.json`, and two of them the agent's rules file.
  `release-asks-before-staging`'s also seeds stub build, deploy, smoke, and rollback
  scripts, a reviewed passing test summary naming HEAD, and the readiness note on HEAD that
  matches it, so nothing before the staging ask needs GitHub or Jira.
  `release-readiness-stops-without-system-suite`'s project.json sets every required key and
  `release_dir` but no `system_test_command`, so the run stops in Step 1 before any suite,
  Jira, or GitHub call.
  `design-feature-stops-at-approval`'s builds a git repo with a local bare `origin`, a small
  appointment module, empty `docs/design` and `docs/adr`, an exceptions log, and the
  reviewer's rules file.
- **`git` may not run inside a run on macOS.** In the 2026-10-23 `ci-failure-adversary-*`
  run, on Claude Code 2.1.309, every with-arm agent reported that `git` failed through the
  `/usr/bin/git` shim and rebuilt both commits by decoding `.git/objects` with Python, so
  the `git archive` export the agent prescribes never ran. In 4 of those 9 runs `mktemp`
  failed too. The agents' replies point to one cause for both: the sandbox's temp directory
  is not writable, and the `xcrun` shim needs a cache file there. That cause is unconfirmed.
  A scaffold's git runs before the sandbox and is unaffected. Cases whose session or agent
  runs git during the run — `plan-project-stops-at-approval`,
  `design-feature-stops-at-approval`, both `release-*` cases, and
  the `ci-failure-adversary-*` and `feature-design-adversary-*` cases — are not yet
  re-measured against this. `results/` is not tracked, so re-run to check it.
- **Not testable without more scaffolding**: anything needing Jira, GitHub itself, or a
  populated `.claude/state/`. The citation contract end-to-end — the highest-value case —
  is in this category: it spans `plan-work` → `implement-phases` → `ci-green` across a
  real delivery. Reaching it needs a `case.yaml` with a `context.scaffold_script` that
  builds a repo and seeds the state file, plus mocked Atlassian tools under `mocks/`.
  That is the next case to write, and it is deliberately not stubbed here: a case that
  cannot fail is worse than an absent one.

## Cost and CI

`llm` graders call a judge model, so this suite is not a required check on every push.
Run it when the stage skills change. `--threshold 1.0` is the default and exits non-zero
on any case below it, so wiring it into a scheduled workflow is a one-line change when
the suite is trusted.

`--judge-model sonnet` is worth passing if a rubric is being failed on formatting rather
than substance.

## Maintaining it

A case that stops failing when its behavior breaks is worse than no case. When a stage
skill changes shape, run the suite against the *old* skill first and confirm the case
still catches the regression it was written for.
