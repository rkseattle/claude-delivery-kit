# delivery-kit

The shared half of the phased-delivery workflow: stage skills, adversary agents, the
universal gates, and the two hooks, plus four standalone skills, `readme-docs`,
`incident-review`, `maintenance-review`, and `retire-system`. Projects keep only what is
genuinely theirs — the commands, thresholds and job names — in `.claude/project.json` and
a pair of mechanics gate files.

## Why this exists

Two projects ran near-identical copies of this workflow and drifted apart. The measured
split was roughly 70% shared: about 39% of all differences were nothing but line
re-wrapping, and improvements flowed in both directions with neither project collecting
them. One project ended up contradicting itself between two of its own files, and ran a
branch guard the other had already replaced after four review rounds found thirteen
bypasses in it.

A single source removes the class. What cannot be shared is declared, not duplicated.

The kit's rules are measured against one source:
`reference/software-engineering-rule-book.md`. A ticket that quotes a rule cites it there.
`reference/rule-book-map.md` names the kit file that applies each rule and exit criterion,
or the `gates/exceptions.md` row recording why none does.

## Layout

```text
.claude-plugin/
  plugin.json          the manifest
  marketplace.json     this repo is also its own marketplace
skills/                plan-project, write-tickets, deliver, plan-work,
                       implement-phases, branch-review, ship-pr, ci-green;
                       release-readiness and release (once per release, after the
                       merges);
                       readme-docs, incident-review, maintenance-review, and
                       retire-system (standalone)
agents/                ticket-, design-, commit-, ci-failure-, greptile- adversaries
gates/                 status-report.md, definition-of-done.md, pre-push.md,
                       read-only-agent.md (the universal halves only),
                       project-config.md, exceptions.md, rule-book-review.md,
                       planning-exit.md, release-readiness.md, and release.md;
                       scripts/sarif_gate.py builds the scanners' git inputs and reads
                       their reports into the gates' verdicts; scripts/project_rules.py
                       holds the project.json rules and self-test helpers the release,
                       review, incident, maintenance, and retirement scripts share;
                       scripts/_vendor holds PyYAML, which the maintenance check reads
                       alert rules with
hooks/                 hooks.json + the two hooks and their self-tests
scripts/ci/            the CI checks, runnable locally; all.sh runs every one
reference/             software-engineering-rule-book.md, the source the rules
                       are measured against; rule-book-map.md, the kit file
                       that applies each rule, or the exception recording why
                       none does
```

The skills reference `${CLAUDE_PLUGIN_ROOT}/gates/*.md`. A reference that resolves to
nothing fails CI's `Bundled-file references resolve` step, and a run would say so rather
than proceed on a gate it could not read.

## Standalone skills

These are not delivery stages: none runs inside `deliver`, and `readme-docs` works with
or without the rest of the kit.

- **`readme-docs`** — loads on its own, by description. It writes, rewrites, or audits a
  project's `README.md` and the docs it links to, with every command and link checked
  against the repo by `skills/readme-docs/scripts/check_readme.py`. It arrives with the
  plugin as `delivery-kit:readme-docs`. To use it without the plugin, copy
  `skills/readme-docs/` to `.claude/skills/readme-docs/` in a repo, or to
  `~/.claude/skills/readme-docs/` for every project; a copy there wins the bare name
  `readme-docs` over the plugin's.

- **`incident-review`** — runs only when invoked by name, since it commits and creates
  tickets: `/delivery-kit:incident-review <incident> <YYYY-MM-DD>`, the rule book's Phase 7
  blameless review, after service is restored. It writes
  `incident_reviews_dir/<date>-<slug>.md` with a timeline, impact, root cause, contributing
  factors, and follow-ups, records `late` when it starts more than five working days
  (Monday to Friday) after the incident, and commits the file on `incident/<date>-<slug>`
  without pushing. Each follow-up becomes a Jira ticket labeled `incident-follow-up` only
  once the service owner approves it. It refuses to start while a delivery plan is running
  and not paused, since the branch guard would undo its branch switch.

- **`maintenance-review`** — runs only when invoked by name, since it creates tickets:
  `/delivery-kit:maintenance-review`, the rule book's Phase 7 ongoing checks. It reports, in
  the session, the service owner and on-call rota, open issues by maintenance type
  (`corrective`, `adaptive`, `perfective`, `preventive`) and those carrying none, the
  `preventive` share of the last iteration's resolved issues, outdated dependencies,
  Dependabot alerts past the patch SLA, runbooks last committed more than 90 days ago, alert
  routes whose target is no one on call, and `incident-follow-up` issues open more than 30
  days, plus each named discipline's maintenance addendum. It writes no file and commits
  nothing, and each ticket it proposes is created only once the service owner approves it.

- **`retire-system`** — runs only when invoked by name, since it commits:
  `/delivery-kit:retire-system <name>`, the rule book's Phase 7 step 7. It writes
  `retirements_dir/<name>.md` with `User notice`, `Data`, `Infrastructure`, and
  `Credentials` sections, each a checklist with a `Status: pending` or `Status: done` line,
  drafts the notice, and lists every data store, resource, and credential the repository
  names — by name and location, never a value. A section becomes `done` only once the
  service owner confirms every item in it, and the record is committed on `retire/<name>`,
  without pushing, only once all four are. It runs no removal and sends no notice: every
  teardown and revocation is the service owner's. Like `incident-review`, it refuses to start
  while a delivery plan is running and not paused.

## Installing in a project

Add to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "rob-kit": {
      "source": { "source": "url", "url": "<this repo's git url>" }
    }
  },
  "enabledPlugins": { "delivery-kit@rob-kit": true }
}
```

During development, `claude --plugin-dir /Users/rob/dev/claude-delivery-kit` loads it
straight from disk with no marketplace.

**Delete the project's own copies when you enable this.** A project skill wins its bare
name, so a leftover `.claude/skills/deliver/` keeps answering `/deliver` while the
plugin's copy sits unused behind `/delivery-kit:deliver`.

## What a project still owns

- `.claude/project.json` — ticket prefix, build/test/lint commands, results paths,
  locale count, and the scope slots the generic gates defer to
- `.claude/gates/*-mechanics.md` — the project's own commands and thresholds
- `.claude/agent-rules/<agent-name>.md` — the project rules each adversary applies
- `.claude/state/` — runtime, gitignored, never part of this repo
- Any project-specific skill (`e2e-authoring`, `swift-testing`)

## agent-rules

The five adversaries share a skeleton — cold-read framing, the never-move-HEAD rule, the
procedure, root-cause discipline, the output block. What differs between projects is one
section each: the rules to attack. Merging two projects' rule lists into one file would
produce a list where most entries are inapplicable noise, so each agent reads its own
rules from the project instead:

```text
.claude/agent-rules/commit-adversary.md
.claude/agent-rules/design-adversary.md
.claude/agent-rules/greptile-reviewer.md
.claude/agent-rules/ci-failure-adversary.md
.claude/agent-rules/ticket-adversary.md
```

Each holds what the project's copy of that agent used to carry inline — architecture
rules, the grep target most often missed, the behavior the automated suite cannot reach
and the gate covering it, and any environmental exception `ci-failure-adversary` may
accept.

A missing file is not an error. Every agent says so in one line and reviews against
`CLAUDE.md` alone, because an agent that invents project rules to fill the gap produces
findings the author cannot distinguish from real ones.

## project.json

Every key, its default, and what reads it: [reference/project-json.md](reference/project-json.md).

## Friction and citations

Stages record two lists to `.claude/state/current-plan.json` as they go, printing nothing:
process friction to `friction[]`, and the external survey behind each design decision to
`citations[]`. `ci-green` reports both once, at the end of delivery, before Step 6 deletes
that file. Two more lists handle pattern spread outside the plan's files:
`pending_spread[]` queues each instance for the stage's next question, and `exclusions[]`
keeps each one declined at that question, so later review stages close findings on it
rather than reopen them. `pr_size_approved_lines` records the size a yes to the pre-push
size question approved.

A citation names the two or three real implementations of the whole problem surveyed
before the decision (`surveyed`), the one it follows (`standard`), and how it was applied
here; the schema is in `skills/implement-phases/SKILL.md`. It is recorded at the decision
because that is the only moment it is knowable — `git log` cannot say afterward which
standard shaped a choice, and a review round's citation never reaches a commit message at
all. `waived` entries name what had no external answer — still listing what was surveyed —
which is where invention becomes visible.

```json
{ "stage": "implement-phases", "phase": 3, "phase_name": "E2E specs",
  "at": "2026-09-10T16:52:35Z", "item": "...", "target_file": "gates/definition-of-done.md",
  "proposed_wording": "...", "displaces": "..." }
```

`phase`/`phase_name` are `null` outside `implement-phases`; `ci-green` records `iteration`
instead. The dedup keeps every origin, because an item hit in three phases is a different
signal from one hit once.

Per-stage reporting split the list across up to four places that could not see each other,
so the same item got proposed repeatedly and each report stopped a run mid-flight for a
config conversation.

## Line budget

`deliver` caps each file so the corpus cannot ratchet upward, and a change that would
breach a cap names what comes out. **The caps themselves live in one place — the table in
`skills/deliver/references/invariants.md`** — and CI enforces them with
`scripts/ci/line-budget.sh`, run by the `Line budget` step. They are deliberately not
repeated here: a second copy drifts from the enforced one, and a reader trusting the stale
copy plans against a cap that does not exist.

A skill's cap covers its `references/` files, counted together with the body. The split
exists to cut what loads per invocation, not to create room the budget cannot see.

`design-adversary.md` sits at its cap. It absorbed two projects' worth of rules, so it is
the likeliest to want to grow; the pressure is the cap working as intended, and the place
for per-dimension detail is `agent-rules/`, not here.

## Hooks

Both run from `${CLAUDE_PLUGIN_ROOT}` and read the project's
`.claude/state/current-plan.json`, which stays project-side. Plugin hooks merge with a
project's own rather than replacing them.

`block-false-stop.sh` refuses to end a turn while an approved plan has unfinished phases.
`protect-plan-branch.sh` puts HEAD back when a command moves it off the plan's branch —
it asks git where HEAD is rather than parsing the command, which is what retired the
predecessor and its Python tokenizer.

The branch guard restores only a branch it has seen HEAD sitting on, recorded in
`.claude/state/branch-adopted`. A snapshot cannot otherwise tell drift from a session that
was never on the branch, and a plan file nothing ever deletes made the second case common:
a new session opening on `main` was dragged onto the stale plan's branch, then dragged back
every time it was asked to leave. Both hooks honor `"paused": true`, which is how a
deliberate switch away from the branch is declared.

Each hook self-tests, taking the path of the hook under test:

```bash
bash hooks/block-false-stop.sh --self-test
bash hooks/protect-plan-branch.sh --self-test
```

Run both after any edit to either. A guard that silently stops guarding looks exactly
like a clean run.
