# delivery-kit

The shared half of the phased-delivery workflow: stage skills, adversary agents, the
universal gates, and the two hooks. Projects keep only what is genuinely theirs — the
commands, thresholds and job names — in `.claude/project.json` and a pair of mechanics
gate files.

## Why this exists

Two projects ran near-identical copies of this workflow and drifted apart. The measured
split was roughly 70% shared: about 39% of all differences were nothing but line
re-wrapping, and improvements flowed in both directions with neither project collecting
them. One project ended up contradicting itself between two of its own files, and ran a
branch guard the other had already replaced after four review rounds found thirteen
bypasses in it.

A single source removes the class. What cannot be shared is declared, not duplicated.

## Layout

```
.claude-plugin/
  plugin.json          the manifest
  marketplace.json     this repo is also its own marketplace
skills/                deliver, plan-work, implement-phases,
                       branch-review, ship-pr, ci-green
agents/                design-, commit-, ci-failure-, greptile- adversaries
gates/                 status-report.md, definition-of-done.md, pre-push.md
                       (the universal halves only)
hooks/                 hooks.json + the two hooks and their self-tests
```

The skills reference `${CLAUDE_PLUGIN_ROOT}/gates/*.md`. Those three files land in the
gates commit; until then the references resolve to nothing and a run would say so rather
than proceed on a gate it could not read.

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

The four adversaries share a skeleton — cold-read framing, the never-move-HEAD rule, the
procedure, root-cause discipline, the output block. What differs between projects is one
section each: the rules to attack. Merging two projects' rule lists into one file would
produce a list where most entries are inapplicable noise, so each agent reads its own
rules from the project instead:

```
.claude/agent-rules/commit-adversary.md
.claude/agent-rules/design-adversary.md
.claude/agent-rules/greptile-reviewer.md
.claude/agent-rules/ci-failure-adversary.md
```

Each holds what the project's copy of that agent used to carry inline — architecture
rules, the grep target most often missed, the behavior the automated suite cannot reach
and the gate covering it, and any environmental exception `ci-failure-adversary` may
accept.

A missing file is not an error. Every agent says so in one line and reviews against
`CLAUDE.md` alone, because an agent that invents project rules to fill the gap produces
findings the author cannot distinguish from real ones.

## project.json

The stage skills carry the procedure; the commands, paths and thresholds come from
`.claude/project.json` in each project. A `{{key}}` in a skill resolves from this file.

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
  "results_file": "<path the local gate writes its verdict to>",
  "results_read_command": "<command that reads counts out of it>",
  "ci_results_artifact": "<name of the uploaded CI result artifact>",
  "verification_tiers": "<the tiers an AC can be verified by>",
  "verification_step_file": ".claude/gates/<what ship-pr must resolve>.md",
  "failure_policy_gate": ".claude/gates/<gate holding the failure policy>.md",
  "mechanics_gate_dod": ".claude/gates/dod-mechanics.md",
  "mechanics_gate_pre_push": ".claude/gates/pre-push-mechanics.md",
  "registry_file": ".claude/registries.md",
  "plan_rules_file": ".claude/plan-rules.md",
  "user_docs_targets": "README.md docs/user-guide.md",
  "extra_gates": [".claude/gates/<project-only gate>.md"]
}
```

A key naming a file the project does not have gets `none`, and the skill says so in one
line rather than inventing a substitute. `verification_step_file` is the one that matters
most: it is where `ship-pr` learns whether this project's diff needs a push-run suite, a
session on real hardware, or nothing beyond the checklist — the single biggest divergence
between the two projects this was extracted from.

## Line budget

`deliver` caps each file so the corpus cannot ratchet upward: 130 lines for an agent
definition, 320 for a skill, 300 for a gate. A change that would breach a cap names what
comes out. These generic files are held to the same caps as the project copies they
replace.

The skill cap was 300 in both projects and is 320 here, raised deliberately rather than
met by compression. `deliver` merges two projects' invariants and adds one rule neither
had — **Shared before project**, which sends a generally-applicable rule to this plugin
instead of a project file. That rule is what stops the drift this repo exists to end, so
it earned the twenty lines rather than being cut to fit.

`greptile-reviewer.md` sits at the cap. It absorbed two projects' review dimensions, so
it is the file most likely to want to grow; the pressure is the cap working as intended,
and the place for per-dimension detail is `agent-rules/`, not here.

## Hooks

Both run from `${CLAUDE_PLUGIN_ROOT}` and read the project's
`.claude/state/current-plan.json`, which stays project-side. Plugin hooks merge with a
project's own rather than replacing them.

`block-false-stop.sh` refuses to end a turn while an approved plan has unfinished phases.
`protect-plan-branch.sh` puts HEAD back when a command moves it off the plan's branch —
it asks git where HEAD is rather than parsing the command, which is what retired the
predecessor and its Python tokenizer.

Each hook self-tests, taking the path of the hook under test:

```bash
bash hooks/block-false-stop.sh --self-test
bash hooks/protect-plan-branch.sh --self-test
```

Run both after any edit to either. A guard that silently stops guarding looks exactly
like a clean run.
