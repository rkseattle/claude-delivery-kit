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
