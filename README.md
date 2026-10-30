# delivery-kit

A Claude Code plugin that takes a Jira ticket from plan to merged PR: phased plan,
adversarial reviews, gated commits and pushes, and CI to green. Each project supplies only
its own commands and thresholds, in `.claude/project.json`.

## Install

Requires:

- Claude Code with plugin support <!-- TODO: confirm the minimum Claude Code version -->
- git 2.31 or later and Python 3.8 or later on `PATH`, and `jq` for the hooks
- the GitHub CLI `gh`, authenticated, for pushing, PRs, and CI
- an Atlassian MCP server connected to the project's Jira, for tickets and transitions

Add the marketplace and enable the plugin in the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "rob-kit": {
      "source": { "source": "github", "repo": "rkseattle/claude-delivery-kit" }
    }
  },
  "enabledPlugins": { "delivery-kit@rob-kit": true }
}
```

To work on the kit itself, load it from a checkout instead:
`claude --plugin-dir <path-to-checkout>`.

Delete any copies of these skills the project already has. A project skill wins its bare
name, so a leftover `.claude/skills/deliver/` keeps answering `/deliver` while the plugin's
copy sits unused behind `/delivery-kit:deliver`.

## Usage

1. Add `.claude/project.json` to the project; see
   [Configure a project](#configure-a-project). Add `.claude/state/`, `docs/plans/`, and
   `docs/tickets/` to its `.gitignore`: runs write their working state there.
2. Run a ticket end to end (`plan-work` asks to split more than three tickets):

   ```text
   /delivery-kit:deliver ABC-123
   ```

3. Approve the plan when it stops and asks. The run then implements, reviews, pushes,
   opens the PR, and watches CI, stopping only for decisions that need you, such as an
   oversized PR or a verification only you can run.
4. Say yes to the merge once CI is green and the PR is approved, or, with no reviewers
   configured, once you approve the recorded review exception.

A run's state lives in `.claude/state/current-plan.json`. A session that is interrupted
picks up where it stopped the next time `/delivery-kit:deliver` runs. Every stage records
friction and citations as it goes, and `ci-green` reports them at the end. Friction items are proposed changes to the
kit, applied only on your yes; citations record the standards the run followed.

Each stage can also run on its own as `/delivery-kit:<stage>`. Use `write-tickets` before
`deliver` to turn a request into plannable tickets, and `release-readiness` then `release`
after the merges.

## How it fits together

Skills are the procedures, agents are the read-only reviewers they call, gates are the
checklists they must pass, and hooks keep a run from stopping early or leaving its branch.
Every skill except `readme-docs` runs only when invoked by name.

- **Before delivery**
  - `plan-project` — writes the project brief and waits for the sponsor's decision.
    Gate: `planning-exit.md`.
  - `design-feature` — writes a feature's design doc and its ADRs, has them reviewed cold,
    and commits them once the tech lead decides. Agent: `feature-design-adversary`.
    Gate: `design-exit.md`.
  - `write-tickets` — turns a request, or an approved design's work plan, into Jira tickets
    that `plan-work` can plan as written. Agent: `ticket-adversary`.
  - `status` `<design path | EPIC-KEY>` — prints where a feature stands between design and
    tickets, and the one command that moves it on. Writes nothing.
- **`deliver`** — runs the five stages below in order and resumes an interrupted run.
  Every stage reads `project-config.md` and reports per `status-report.md`; `deliver`
  records rule-book exceptions in the `exceptions.md` format.
  1. `plan-work` — reads the tickets, the code, and any approved design their Epic names,
     writes a phased plan, and stops for approval. Agent: `design-adversary`.
  2. `implement-phases` — branches, moves Jira to In Progress, and commits each phase.
     Agent: `commit-adversary` before every commit. Gate: `definition-of-done.md`.
  3. `branch-review` — a cold review of the whole branch, with each fix spread to every
     instance of its cause. Agents: `greptile-reviewer`, then `commit-adversary` on the
     fixes. Gate: `definition-of-done.md`.
  4. `ship-pr` — pushes, opens the PR, requests reviewers, and moves Jira to In Review.
     Gate: `pre-push.md`.
  5. `ci-green` — loops on CI failures and review comments until green and approved, then
     merges on the tech lead's yes. Agent: `ci-failure-adversary`. Gate: `pre-push.md`
     before each re-push.
- **After the merges**
  - `release-readiness` `<version>` — the release gate: system, integration, and
    non-functional suites and open defects. Gate: `release-readiness.md`.
  - `release` `<version>` — tags, builds once, and rolls out stage by stage with a tested
    rollback. Gate: `release.md`.
- **Standalone**
  - `readme-docs` — writes or audits a README and its linked docs, checked by
    `check_readme.py`. Loads on its own when you ask about docs. To use it without the
    plugin, copy `skills/readme-docs/` to `.claude/skills/` or `~/.claude/skills/`; a copy
    there takes the bare name `readme-docs` over the plugin's.
  - `incident-review` `<incident> <YYYY-MM-DD>` — a blameless review after an incident,
    committed on its own branch.
  - `maintenance-review` — reports ownership, dependency, vulnerability, runbook, and alert
    health. Writes nothing.
  - `retire-system` `<name>` — the record and checklist for shutting a system down.
  - `plan-project`, `design-feature`, `incident-review`, and `retire-system` each refuse to
    start while a delivery plan is running and not paused.

Agents (each reads `read-only-agent.md` and never changes the repo):

- `design-adversary` — attacks a plan before approval.
- `feature-design-adversary` — attacks a feature design doc against `design-exit.md` before
  approval.
- `commit-adversary` — attacks a diff before it is committed, or, from any stage, a claim
  that a defect is safe to defer.
- `greptile-reviewer` — reviews a whole branch cold before the PR.
- `ci-failure-adversary` — checks that a CI fix addresses the root cause.
- `ticket-adversary` — checks that a ticket draft can be planned as written.

Gates:

- `project-config.md` — how every skill reads `project.json` and resolves missing keys.
- `definition-of-done.md` — the checks before every commit.
- `pre-push.md` — the checks before every push and PR.
- `status-report.md` — the report printed at every phase and stage boundary.
- `read-only-agent.md` — the rule that keeps every agent from changing the repo.
- `agent-rules.md` — where every agent reads its project's rules, and what an absent file
  means.
- `rule-book-review.md` — the rule-book checks the commit, branch, and CI reviewers apply.
- `exceptions.md` — the format of a project's rule-book exceptions register.
- `planning-exit.md` — the rule book's Phase 1 gate: no implementation before the brief
  is approved.
- `design-exit.md` — the rule book's Phase 3 gate at feature scale: the design doc's
  sections, its ADRs, and who approves it.
- `release-readiness.md` — the rule book's Phase 5 gate a version must pass to release.
- `release.md` — the rule book's Phase 6 gate: tag, staged rollout, and rollback.

Hooks (`hooks/hooks.json`):

- `block-false-stop.sh` — on Stop, refuses to end a turn while the plan has unfinished
  phases, unless the run set `"paused": true`.
- `protect-plan-branch.sh` — after each Bash command, puts HEAD back on the plan's branch
  if the command moved it, unless the run set `"paused": true`.

## Configure a project

A project keeps only what is its own:

- `.claude/project.json` — ticket prefix, build and test commands, result files, roles, and
  the other keys the skills read. Every key and its default:
  [reference/project-json.md](reference/project-json.md).
- `.claude/gates/*-mechanics.md` — the commands behind the Definition of Done and the
  pre-push checklist.
- `.claude/agent-rules/<agent-name>.md` — the rules each agent attacks: architecture
  rules, the grep target most often missed, the behavior the automated suite cannot reach
  and the gate covering it, and any environmental exception `ci-failure-adversary` may
  accept. A missing file is fine; `gates/agent-rules.md` says what the agent judges against
  instead.
- `.claude/state/` — run state; keep it gitignored.

The kit's rules are measured against
[reference/software-engineering-rule-book.md](reference/software-engineering-rule-book.md).
[reference/rule-book-map.md](reference/rule-book-map.md) names the file that applies each
rule.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
