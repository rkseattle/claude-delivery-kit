---
description: A design that meets every design-exit rule draws zero BLOCKERs from the dispatched feature-design-adversary
max_turns: 30
timeout_seconds: 900
allowed_tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Agent
  - WebSearch
  - WebFetch
tags:
  - adversarial-review
  - false-positive
---

Dispatch the `delivery-kit:feature-design-adversary` agent with the Agent tool to review
the design doc at `docs/design/per-endpoint-webhook-rate-limits.md` in this workspace.
Its prompt is that file's absolute path and nothing else: run `pwd` to build it, and add
no request, summary, or hint.

The repository the design cites is absent: this workspace holds no git history and none
of the files its `Current state` names, so a claim about that code cannot be checked and
is UNVERIFIABLE, not a BLOCKER. The project's `disciplines` is `[]`, so the design carries
no `Threat model` section. The agent reads both facts itself, from
`.claude/agent-rules/feature-design-adversary.md` and `.claude/project.json`; do not pass
them on.

Return the agent's report exactly as it returns it. If the dispatch fails, reply with
its error and nothing else: do not review the design yourself.
