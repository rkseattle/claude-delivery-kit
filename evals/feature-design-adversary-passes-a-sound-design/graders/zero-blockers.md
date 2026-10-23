---
type: llm
---

The design under review meets every rule of `gates/design-exit.md`. All 21 sections it
needs are present in order, with no `Threat model`, since `disciplines` is `[]`. Each
`SM<n>` is named by the one handoff, which lists two tickets and three phases. The one
`NFR1` line names `rate_limiter`, a module `Components and interfaces` defines. It holds no
`Costly to reverse` line, so no ADR has to exist. Every one of its four rollout steps names
its rollback step. `agents/feature-design-adversary.md` defines BLOCKER as exactly six
kinds, and none applies.

The repository the design cites is absent from the workspace. A kind-2 BLOCKER needs the
cited `file:line` to contradict the claim, citing the disproving line; an absent file has
no such line, so each `Current state` claim is UNVERIFIABLE.

PASS when the response's `## BLOCKER` section is empty or says there are none. MAJOR,
MINOR, and UNVERIFIABLE findings do not affect this grader.

FAIL when the response does any of:

- reports any BLOCKER, including one raised because a file `Current state` cites is
  missing from the workspace, which is a claim it could not check, not one the code
  contradicts
- says the design must not proceed, or asks for a change before it may, in a question,
  caveat, or verdict outside the `## BLOCKER` heading
- is not a review of the design, such as a reply that the agent could not be dispatched

This is the false-positive partner of `feature-design-adversary-catches-a-missing-rollback`,
whose design differs from this one only in step 3's rollback: a reviewer that blocks every
design passes that case and fails this one.
