# Contributing to delivery-kit

## Run the checks

Every CI step has a local equivalent. They need git, Python 3.8 or later, `jq`, `curl`, and `shasum`
(`shellcheck.sh` downloads a pinned shellcheck). Run them all, in CI's order, from the repo
root after `git add` (`json-parses.sh` reads tracked files only):

```sh
bash scripts/ci/all.sh
```

`.claude/gates/pre-push-mechanics.md` maps each CI step to its command. A step added to
`.github/workflows/ci.yml` also gets a line in `scripts/ci/all.sh` and a row in that table;
`scripts/ci/ci-steps-mirrored.sh` fails CI otherwise.

The skills reference `${CLAUDE_PLUGIN_ROOT}/gates/*.md`. A reference that resolves to
nothing fails CI's `Bundled-file references resolve` step, and a run would say so rather
than proceed on a gate it could not read.

## Layout

```text
.claude-plugin/
  plugin.json          the manifest
  marketplace.json     this repo is also its own marketplace
skills/                one directory per skill; the README lists them
agents/                the six reviewers; the README lists them
gates/                 the universal halves of the gates, listed in the README;
                       scripts/sarif_gate.py builds the scanners' git inputs and reads
                       their reports into the gates' verdicts; scripts/adr_numbers.py
                       fails decision records sharing a number; scripts/project_rules.py
                       holds the project.json key registry and rules, check-script
                       entry point, and self-test helpers the release, review,
                       incident, maintenance, retirement, and design scripts share;
                       scripts/_vendor holds PyYAML, which the maintenance check reads
                       alert rules with
hooks/                 hooks.json + the two hooks and their self-tests
scripts/ci/            the CI checks, runnable locally; all.sh runs every one
evals/                 the claude plugin eval suite; see evals/README.md
reference/             software-engineering-rule-book.md, the source the rules
                       are measured against; rule-book-map.md, the kit file
                       that applies each rule, or the exception recording why
                       none does; project-json.md, every project.json key and
                       its default; exceptions-log.md, this repo's own
                       exceptions register
```

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

## Line budget

`deliver` caps each file so the corpus cannot ratchet upward, and a change that would
breach a cap names what comes out. **The caps themselves live in one place — the table in
`skills/deliver/references/invariants.md`** — and CI enforces them with
`scripts/ci/line-budget.sh`, run by the `Line budget` step. They are deliberately not
repeated here: a second copy drifts from the enforced one, and a reader trusting the stale
copy plans against a cap that does not exist.

A skill's cap covers its `references/` files, counted together with the body. The split
exists to cut what loads per invocation, not to create room the budget cannot see.

`design-adversary.md` sits at its cap. It absorbed several projects' worth of rules, so it is
the likeliest to want to grow; the pressure is the cap working as intended, and the place
for per-dimension detail is `agent-rules/`, not `agents/design-adversary.md`.

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

A `friction[]` entry:

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

