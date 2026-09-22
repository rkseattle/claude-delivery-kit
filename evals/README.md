# Eval suite

Behavioral tests for the stage skills. CI checks that the kit's files are *well-formed*;
this suite asks whether the skills still *do what they claim*.

```bash
claude plugin eval .
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
| `write-tickets-stops-without-config` | Tickets drafted against verification tiers and source roots the project never declared | not yet measured |
| `design-adversary-passes-a-sound-plan` | Review that always finds a blocker, so planning always ends in deferred work | not yet measured |
| `design-adversary-catches-a-missing-ac` | Review that stopped blocking real defects after its BLOCKER definition was narrowed | not yet measured |

Each case pairs a check on the *result* with a check on *how Claude got there*, per the
official guidance: a `regex` or `llm` grader on the reply, and a `tool_used` grader on
the transcript.

**Δ is the number that matters, not the score.** A case scoring 1.00 in both arms is
measuring what the model already knew. The deltas above are from the run of
2026-09-14 against Opus 5; re-measure rather than trusting them after a model change.

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

**Its known weakness is the arms.** The baseline arm has no `agents/design-adversary.md` to
read, so it reviews with no instructions at all and may well return zero BLOCKERs by
default. A small or negative Δ here therefore does not mean the plugin is not working — it
means the baseline had nothing to over-apply. **Read the with-arm score directly** for this
case; Δ is not the number that matters, unusually for this suite. Read the findings
themselves too: the graders check severity and remedy, and a with-arm that passes both
while listing useful MAJORs is the target behavior, not a near miss.

The case is also **not a regression test for under-reviewing**. Nothing here would catch a
reviewer that has stopped finding real blockers, because a sound plan gives it nothing to
miss. That is what `design-adversary-catches-a-missing-ac` is for, and **the two are read
together or not at all.**

That case plants one defect — ABC-207's fourth acceptance criterion, rate limiting, is in
the ticket and in no phase — and requires it back as a BLOCKER, not as a MINOR or a
question. Narrowing BLOCKER to three things was the largest change made to the reviewer,
and this is the case that says the narrowing cost nothing.

Passing one alone means little in either direction. A reviewer that blocks nothing passes
the sound-plan case and fails this one; a reviewer that blocks everything does the reverse.
Only both passing says the severity line sits where it was meant to.

## What these cases cannot test

`tool_used: Skill` is the natural grader for "did the plugin fire", and it is
**unsatisfiable here**. Every stage skill carries `disable-model-invocation: true`, so
the model is structurally unable to invoke one; a slash command in a prompt body reaches
the run as literal text rather than as an invocation, since the harness sends the body
exactly as written.

What the with-arm measures instead is the plugin's *files being present, findable, and
followed*. That is a real difference — the baseline arm scores 0.00 on
`deliver-reads-stage-files` and costs nothing, because it has nothing to read — but it is
not proof that slash-command routing works. Nothing in this harness can prove that.

## What the sandbox allows, and what it rules out

Every run starts in an **empty workspace**. No project `.claude/`, no `CLAUDE.md`, no MCP
servers, no user settings. That constrains what can be tested here:

- **Testable**: whether a stage reads its files, whether it refuses without configuration,
  whether planning stops at the approval gate, the shape of what it produces.
- **Not testable without scaffolding**: anything needing Jira, a git history, or a
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
