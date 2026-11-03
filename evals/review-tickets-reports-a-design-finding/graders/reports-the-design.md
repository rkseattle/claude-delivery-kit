---
type: llm
---

The Epic's design, `docs/design/per-endpoint-webhook-rate-limits.md`, is accepted on
`main`. Its `## Rollout and rollback` has four numbered steps, and step 3, turning on
`endpoint_rate_limits` for the five internal test endpoints, names no rollback step:
BLOCKER kind 5 of `feature-design-adversary`. ABC-1 and its child ABC-2 meet the rubric.

PASS when the response has a design section separate from the ticket sections that
reports step 3's missing rollback as a BLOCKER, ends that section with
`NEXT: /delivery-kit:design-feature ABC-1` followed by the BLOCKER and MAJOR findings
quoted, and keeps every design finding out of the ticket sections and their PASS/FAIL
counts.

FAIL when the response does any of:

- does not mention step 3's missing rollback, or reports it below BLOCKER
- reports a design finding under ABC-1 or ABC-2, or counts it in a ticket's result
- says the design was not checked
- reviews the design itself rather than reporting the dispatched agent's findings
